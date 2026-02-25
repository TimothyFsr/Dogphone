"""
Load DogPhone config from environment or config.env file.
"""
# Bump this when you release; shown on status page and in Telegram /version
VERSION = "1.0.0"

import os
import socket
from pathlib import Path

# Prefer repo root config; fallback to pi/config.env or env vars only
CONFIG_PATHS = [
    Path(__file__).resolve().parent.parent / "config" / "config.env",
    Path(__file__).resolve().parent / "config.env",
]


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip()
                if k and v and not os.environ.get(k):
                    os.environ[k] = v


def load_config() -> dict:
    for p in CONFIG_PATHS:
        _load_dotenv(p)
    hostname = socket.gethostname()
    return {
        "telegram_bot_token": os.environ.get("TELEGRAM_BOT_TOKEN", "").strip(),
        "telegram_chat_id": os.environ.get("TELEGRAM_CHAT_ID", "").strip(),
        "jitsi_room": os.environ.get("JITSI_ROOM", f"DogPhone-{hostname}").strip(),
        "jitsi_domain": os.environ.get("JITSI_DOMAIN", "meet.jit.si"),
        "button_gpio": int(os.environ.get("BUTTON_GPIO", "17")),
        "servo_gpio": int(os.environ.get("SERVO_GPIO", "27")),
        "servo_pulse_min": float(os.environ.get("SERVO_PULSE_MIN", "0.5")),
        "servo_pulse_max": float(os.environ.get("SERVO_PULSE_MAX", "2.5")),
        "setup_port": int(os.environ.get("SETUP_PORT", "8765")),
    }


def get_jitsi_url(cfg: dict) -> str:
    room = cfg["jitsi_room"].replace(" ", "")
    domain = cfg["jitsi_domain"].rstrip("/")
    # Disable Jitsi's pre-join screen so the Pi joins the room directly.
    return f"https://{domain}/{room}#config.prejoinConfig.enabled=false"
