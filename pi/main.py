#!/usr/bin/env python3
"""
DogPhone – Raspberry Pi main app.

- Button press: open Zoom video call in browser (no Telegram).
- Treat: use Zoom (e.g. raise hand / message in meeting) or the "Dispense treat" button on the status page.

Run: python main.py
"""
import logging
import os
import subprocess
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import load_config, get_call_url, VERSION

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("dogphone")

try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False
    GPIO = None

CONTROL_PORT = 8766
_cfg = None


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
        pwm = GPIO.PWM(pin, 50)
        pwm.start(0)
        duty = (cfg["servo_pulse_min"] + cfg["servo_pulse_max"]) / 2
        pwm.ChangeDutyCycle(duty)
        import time
        time.sleep(0.5)
        pwm.ChangeDutyCycle(0)
        pwm.stop()
        log.info("Servo triggered (treat dispensed)")
    except Exception as e:
        log.warning("Servo trigger failed: %s", e)


def open_video_call_in_browser(url: str) -> None:
    """Open video call URL in Chromium (kiosk) so camera/mic are used for the call."""
    display = os.environ.get("DISPLAY", ":0")
    cmd = [
        "chromium-browser",
        "--kiosk",
        "--autoplay-policy=no-user-gesture-required",
        "--use-fake-ui-for-media-stream",
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


def _on_button_press():
    """Called when GPIO button is pressed: open Zoom."""
    global _cfg
    if not _cfg:
        return
    url = get_call_url(_cfg)
    if url:
        open_video_call_in_browser(url)


def setup_gpio_button(cfg: dict) -> None:
    """Start a thread that listens for GPIO button press."""
    if not HAS_GPIO or not cfg.get("video_call_url"):
        return
    pin = cfg["button_gpio"]
    def loop():
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(pin, GPIO.FALLING, callback=lambda c: _on_button_press(), bouncetime=3000)
            log.info("Button on GPIO %s enabled", pin)
        except Exception as e:
            log.warning("Could not setup button GPIO %s: %s", pin, e)
    t = threading.Thread(target=loop, daemon=True)
    t.start()


def create_app(cfg: dict):
    from flask import Flask
    app = Flask(__name__)

    @app.route("/")
    def home():
        standby = Path(__file__).resolve().parent / "standby.html"
        if standby.exists():
            return open(standby).read()
        return "<h1>DogPhone</h1><p><a href='/trigger-call'>Test call</a> | <a href='/dispense'>Dispense treat</a></p>"

    @app.route("/trigger-call")
    def trigger_call():
        url = get_call_url(cfg)
        if not url:
            return "<h1>Not configured</h1><p>Set VIDEO_CALL_URL in config.</p>", 503
        open_video_call_in_browser(url)
        return (
            "<!DOCTYPE html><html><body style='font-family:sans-serif;padding:2rem;'>"
            "<h1>Call started</h1><p>Zoom opened on the Pi. Join the same meeting on your phone.</p> "
            "<a href='/'>Back</a></p></body></html>"
        )

    @app.route("/dispense")
    def dispense():
        run_servo_once(cfg)
        return (
            "<!DOCTYPE html><html><body style='font-family:sans-serif;padding:2rem;'>"
            "<h1>Treat dispensed</h1><p><a href='/'>Back</a></p></body></html>"
        )

    return app


def main() -> None:
    global _cfg
    cfg = load_config()
    _cfg = cfg

    call_url = get_call_url(cfg)
    if not call_url:
        log.error("Set VIDEO_CALL_URL in config (e.g. your Zoom Meeting ID or URL).")
        sys.exit(1)
    log.info("Call URL: %s", call_url)

    setup_gpio_button(cfg)

    log.info("DogPhone running. Press the button to call (or use Test call on status page). Treat: use Zoom or Dispense on status page.")

    app = create_app(cfg)
    app.run(host="127.0.0.1", port=CONTROL_PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
