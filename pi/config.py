"""
Load DogPhone config from environment or config.env file.
"""
# Bump this when you release; shown on status page and in Telegram /version
VERSION = "1.0.0"

import os
from urllib.parse import quote_plus
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
    return {
        "video_call_url": os.environ.get("VIDEO_CALL_URL", "").strip(),
        "video_call_password": os.environ.get("VIDEO_CALL_PASSWORD", "").strip(),
        "button_gpio": int(os.environ.get("BUTTON_GPIO", "17")),
        "servo_gpio": int(os.environ.get("SERVO_GPIO", "27")),
        "servo_pulse_min": float(os.environ.get("SERVO_PULSE_MIN", "0.5")),
        "servo_pulse_max": float(os.environ.get("SERVO_PULSE_MAX", "2.5")),
        "setup_port": int(os.environ.get("SETUP_PORT", "8765")),
    }


def get_call_url(cfg: dict) -> str:
    """URL to open for the video call (Zoom, Whereby, etc.). Optionally append VIDEO_CALL_PASSWORD as ?pwd= or &pwd=."""
    raw = (cfg.get("video_call_url") or "").strip()
    if not raw:
        return ""
    # If it looks like a Zoom meeting ID (digits, maybe with spaces/dashes), use zoom.us/j/
    meeting_id = raw.replace(" ", "").replace("-", "").replace("\u00a0", "")
    if meeting_id.isdigit():
        raw = f"https://zoom.us/j/{meeting_id}"
    elif not raw.startswith("http://") and not raw.startswith("https://"):
        raw = "https://" + raw
    password = (cfg.get("video_call_password") or "").strip()
    if password:
        sep = "&" if "?" in raw else "?"
        raw = f"{raw}{sep}pwd={quote_plus(password)}"
    return raw
