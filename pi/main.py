#!/usr/bin/env python3
"""
DogPhone – Raspberry Pi main app.

- Button press: open video call (Zoom URL) + send Telegram "your dog is calling" with link.
- Telegram /cookie (or "cookie"): trigger servo to dispense treat.

Run: python main.py
"""
import asyncio
import logging
import os
import subprocess
import sys
import threading
from pathlib import Path

# Add pi dir so config can be found when run from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import load_config, get_call_url, VERSION

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


def open_standby_screen() -> None:
    """Show a 'DogPhone ready' screen on the display."""
    standby_path = Path(__file__).resolve().parent / "standby.html"
    if not standby_path.exists():
        return
    url = standby_path.as_uri()  # file:///path/to/standby.html
    display = os.environ.get("DISPLAY", ":0")
    cmd = [
        "chromium-browser",
        "--kiosk",
        "--noerrdialogs",
        "--disable-infobars",
        url,
    ]
    try:
        subprocess.Popen(
            cmd,
            env={**os.environ, "DISPLAY": display},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        log.info("Opened standby screen")
    except FileNotFoundError:
        pass


def open_video_call_in_browser(url: str) -> None:
    """Open video call URL in Chromium (kiosk) so camera/mic are used for the call."""
    display = os.environ.get("DISPLAY", ":0")
    cmd = [
        "chromium-browser",
        "--kiosk",
        "--autoplay-policy=no-user-gesture-required",
        "--use-fake-ui-for-media-stream",  # auto-allow cam/mic in kiosk
        url,
    ]
    try:
        subprocess.Popen(
            cmd,
            env={**os.environ, "DISPLAY": display},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        log.info("Opened video call in browser: %s", url)
    except FileNotFoundError:
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
    """Called when the call button is pressed: open video call URL + notify owner."""
    url = get_call_url(cfg)
    open_video_call_in_browser(url)
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


async def version_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /version – show installed version."""
    await update.message.reply_text(f"DogPhone version {VERSION}")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start – brief help."""
    await update.message.reply_text(
        "DogPhone 🐕\n\n"
        "• When your dog presses the button, you’ll get a link to join the video call.\n"
        "• Send /cookie to dispense a treat.\n"
        "• Send /update to pull the latest from GitHub and restart."
    )


async def update_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /update – git pull and reboot."""
    await update.message.reply_text("Checking for updates…")
    try:
        from update_check import run_update
        ok, msg = run_update()
        if ok:
            await update.message.reply_text(f"✅ {msg} Restarting the device now…")
            subprocess.Popen(
                ["sudo", "reboot"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            await update.message.reply_text(f"❌ Update failed: {msg}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# Shared state for the test-call HTTP server (no physical button)
_control_cfg = None
_control_bot = None
_control_loop = None
CONTROL_PORT = 8766


def _run_trigger_call_server():
    """Run a minimal Flask server for the 'Test call' button (daemon thread)."""
    try:
        from flask import Flask
        app = Flask(__name__)

        @app.route("/trigger-call")
        def trigger_call():
            global _control_cfg, _control_bot, _control_loop
            if not _control_cfg or not _control_bot:
                return "<h1>Not ready</h1><p>App still starting.</p>", 503
            url = get_call_url(_control_cfg)
            open_video_call_in_browser(url)
            chat_id = _control_cfg.get("telegram_chat_id")
            if chat_id and _control_bot and _control_loop:
                try:
                    future = asyncio.run_coroutine_threadsafe(
                        _control_bot.send_message(
                            chat_id=chat_id,
                            text=f"🐕 Your dog is calling!\n\nJoin the video call:\n{url}",
                        ),
                        _control_loop,
                    )
                    future.result(timeout=10)
                except Exception as e:
                    log.warning("Test call Telegram send failed: %s", e)
            return (
                "<!DOCTYPE html><html><body style='font-family:sans-serif;padding:2rem;'>"
                "<h1>Call started</h1><p>Check your Telegram for the link. "
                "<a href='/'>Back</a></p></body></html>"
            )

        @app.route("/")
        def home():
            standby = Path(__file__).resolve().parent / "standby.html"
            if standby.exists():
                return open(standby).read()
            return "<h1>DogPhone</h1><p><a href='/trigger-call'>Test call</a></p>"

        app.run(host="127.0.0.1", port=CONTROL_PORT, debug=False, use_reloader=False)
    except Exception as e:
        log.warning("Control server failed: %s", e)


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


def main() -> None:
    """Entry point – use python-telegram-bot's run_polling to manage the event loop."""
    if Application is None:
        log.error("Install Telegram: pip install python-telegram-bot")
        sys.exit(1)
    cfg = load_config()
    if not cfg["telegram_bot_token"] or not cfg["telegram_chat_id"]:
        log.error("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in config.env or environment.")
        sys.exit(1)

    call_url = get_call_url(cfg)
    if not call_url:
        log.error("Set VIDEO_CALL_URL in config (e.g. your Zoom Personal Meeting link).")
        sys.exit(1)
    log.info("Call URL: %s", call_url)

    application = (
        Application.builder()
        .token(cfg["telegram_bot_token"])
        .build()
    )
    application.bot_data["cfg"] = cfg

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("cookie", cookie_command))
    application.add_handler(CommandHandler("update", update_command))
    application.add_handler(CommandHandler("version", version_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, cookie_message))

    async def post_init(app: Application) -> None:
        """Called by PTB after initialization, inside the running event loop."""
        loop = asyncio.get_running_loop()
        setup_gpio_button(cfg, loop, app.bot)

        global _control_cfg, _control_bot, _control_loop
        _control_cfg, _control_bot, _control_loop = cfg, app.bot, loop
        t = threading.Thread(target=_run_trigger_call_server, daemon=True)
        t.start()

        log.info(
            "DogPhone running. Press the button to call (or use Test call on screen); "
            "send /cookie in Telegram to treat."
        )

    application.post_init = post_init  # type: ignore[attr-defined]

    # Synchronous call; PTB manages the asyncio loop internally.
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
