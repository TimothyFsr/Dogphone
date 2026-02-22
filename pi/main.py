#!/usr/bin/env python3
"""
DogPhone – Raspberry Pi main app.

- Button press: open Jitsi video room + send Telegram "your dog is calling" with link.
- Telegram /cookie (or "cookie"): trigger servo to dispense treat.

Run: python main.py
"""
import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path

# Add pi dir so config can be found when run from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import load_config, get_jitsi_url

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("dogphone")

# Optional GPIO (only on Pi with RPi.GPIO)
try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False
    GPIO = None

# Telegram
try:
    from telegram import Update, Bot
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
except ImportError:
    Update = Bot = Application = CommandHandler = MessageHandler = filters = ContextTypes = None


def run_servo_once(cfg: dict) -> None:
    """Trigger servo on SERVO_GPIO (one short movement)."""
    if not HAS_GPIO or GPIO is None:
        log.info("(no GPIO) servo trigger skipped")
        return
    pin = cfg["servo_gpio"]
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(pin, GPIO.OUT)
        pwm = GPIO.PWM(pin, 50)  # 50 Hz
        pwm.start(0)
        # Short pulse to move servo (adjust for your mechanism)
        duty = (cfg["servo_pulse_min"] + cfg["servo_pulse_max"]) / 2
        pwm.ChangeDutyCycle(duty)
        import time
        time.sleep(0.5)
        pwm.ChangeDutyCycle(0)
        pwm.stop()
        log.info("Servo triggered (cookie dispensed)")
    except Exception as e:
        log.warning("Servo trigger failed: %s", e)


def open_jitsi_in_browser(url: str) -> None:
    """Open Jitsi room in Chromium (kiosk) so camera/mic are used for the call."""
    display = os.environ.get("DISPLAY", ":0")
    cmd = [
        "chromium-browser",
        "--kiosk",
        "--autoplay-policy=no-user-gesture-required",
        "--use-fake-ui-for-media-stream",  # optional: auto-allow cam/mic in kiosk
        url,
    ]
    try:
        subprocess.Popen(
            cmd,
            env={**os.environ, "DISPLAY": display},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        log.info("Opened Jitsi in browser: %s", url)
    except FileNotFoundError:
        # Fallback: try xdg-open or default browser
        try:
            subprocess.Popen(
                ["xdg-open", url],
                env={**os.environ, "DISPLAY": display},
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            log.warning("Could not open browser; open this URL on your phone: %s", url)


async def on_button_call(cfg: dict, bot: Bot) -> None:
    """Called when the call button is pressed: open Jitsi + notify owner."""
    url = get_jitsi_url(cfg)
    open_jitsi_in_browser(url)
    chat_id = cfg["telegram_chat_id"]
    if chat_id and bot:
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=f"🐕 Your dog is calling!\n\nJoin the video call:\n{url}",
            )
            log.info("Sent Telegram call notification")
        except Exception as e:
            log.warning("Failed to send Telegram notification: %s", e)
    else:
        log.warning("No Telegram chat ID or bot; open on your phone: %s", url)


async def cookie_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cookie – dispense treat."""
    cfg = context.bot_data.get("cfg")
    if not cfg:
        await update.message.reply_text("Configuration not loaded.")
        return
    run_servo_once(cfg)
    await update.message.reply_text("🍪 Cookie sent! Treat dispensed.")


async def cookie_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle plain text 'cookie' (no slash)."""
    if update.message and update.message.text:
        if update.message.text.strip().lower() == "cookie":
            await cookie_command(update, context)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start – brief help."""
    await update.message.reply_text(
        "DogPhone 🐕\n\n"
        "• When your dog presses the button, you’ll get a link to join the video call.\n"
        "• Send /cookie to dispense a treat."
    )


def setup_gpio_button(cfg: dict, loop: asyncio.AbstractEventLoop, bot: Bot) -> None:
    """Register GPIO button; on press, run on_button_call in the event loop."""
    if not HAS_GPIO or not bot or not cfg["telegram_bot_token"]:
        return
    pin = cfg["button_gpio"]
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        # Debounce: only trigger on falling edge (button down)
        def on_press(channel):
            asyncio.run_coroutine_threadsafe(on_button_call(cfg, bot), loop)
        GPIO.add_event_detect(pin, GPIO.FALLING, callback=on_press, bouncetime=3000)
        log.info("Button on GPIO %s enabled", pin)
    except Exception as e:
        log.warning("Could not setup button GPIO %s: %s", pin, e)


async def main_async() -> None:
    if Application is None:
        log.error("Install Telegram: pip install python-telegram-bot")
        sys.exit(1)
    cfg = load_config()
    if not cfg["telegram_bot_token"] or not cfg["telegram_chat_id"]:
        log.error("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in config.env or environment.")
        sys.exit(1)

    application = (
        Application.builder()
        .token(cfg["telegram_bot_token"])
        .build()
    )
    application.bot_data["cfg"] = cfg

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("cookie", cookie_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, cookie_message))

    loop = asyncio.get_event_loop()
    setup_gpio_button(cfg, loop, application.bot)

    log.info("DogPhone running. Press the button to call; send /cookie in Telegram to treat.")
    await application.run_polling(allowed_updates=Update.ALL_TYPES)


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
