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
        # If set, use this URL for calls instead of Jitsi (e.g. Zoom PMI or Whereby room)
        "video_call_url": os.environ.get("VIDEO_CALL_URL", "").strip(),
        "button_gpio": int(os.environ.get("BUTTON_GPIO", "17")),
        "servo_gpio": int(os.environ.get("SERVO_GPIO", "27")),
        "servo_pulse_min": float(os.environ.get("SERVO_PULSE_MIN", "0.5")),
        "servo_pulse_max": float(os.environ.get("SERVO_PULSE_MAX", "2.5")),
        "setup_port": int(os.environ.get("SETUP_PORT", "8765")),
    }


def get_jitsi_url(cfg: dict) -> str:
    room = cfg["jitsi_room"].replace(" ", "")
    domain = cfg["jitsi_domain"].rstrip("/")
    # Disable pre-join screen so the Pi joins directly; disable lobby so the phone joins without "accept"
    opts = "config.prejoinConfig.enabled=false&config.enableLobby=false"
    return f"https://{domain}/{room}#{opts}"


def get_call_url(cfg: dict) -> str:
    """URL to open for the video call. If VIDEO_CALL_URL is set (e.g. Zoom or Whereby), use that; else Jitsi."""
    if cfg.get("video_call_url"):
        return cfg["video_call_url"]
    return get_jitsi_url(cfg)
