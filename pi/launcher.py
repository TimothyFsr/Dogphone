#!/usr/bin/env python3
"""
DogPhone launcher: show setup on screen (with QR) if not configured, else run main app.
Run this on boot so the display shows either the setup wizard or the normal app.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import load_config

SETUP_PORT = 8765
# Use --kiosk for full-screen; add --disable-close to prevent accidental close, or omit for closable window
BROWSER_CMD = ["chromium-browser", "--kiosk", "--noerrdialogs", "--disable-infobars"]


def is_configured() -> bool:
    cfg = load_config()
    return bool(cfg.get("telegram_bot_token") and cfg.get("telegram_chat_id"))


def start_setup_server():
    """Run setup server in background (this process or subprocess)."""
    import threading
    try:
        from setup_server import create_app
        from flask import Flask
        cfg = load_config()
        port = cfg.get("setup_port", SETUP_PORT)
        app = create_app()
        def run():
            app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)
        t = threading.Thread(target=run, daemon=True)
        t.start()
        time.sleep(1)
        return True
    except Exception as e:
        print("Setup server failed:", e, file=sys.stderr)
        return False


def open_browser(url: str):
    display = os.environ.get("DISPLAY", ":0")
    try:
        subprocess.Popen(
            BROWSER_CMD + [url],
            env={**os.environ, "DISPLAY": display},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        try:
            subprocess.Popen(
                ["xdg-open", url],
                env={**os.environ, "DISPLAY": display},
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            pass


def run_main_app():
    """Run the real DogPhone app (blocking)."""
    main_py = Path(__file__).resolve().parent / "main.py"
    os.execv(sys.executable, [sys.executable, str(main_py)])


def start_wifi_ap():
    """Start DogPhone-Setup WiFi hotspot so phone can connect (optional)."""
    script = Path(__file__).resolve().parent / "start_setup_ap.sh"
    if not script.exists():
        return
    try:
        subprocess.Popen(
            ["bash", str(script)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(3)
    except Exception:
        pass


def try_startup_update():
    """If this is a git repo and we have network, pull latest (non-blocking, best-effort)."""
    repo_root = Path(__file__).resolve().parent.parent
    if not (repo_root / ".git").exists():
        return
    try:
        import subprocess
        subprocess.run(
            ["git", "pull", "origin", "main"],
            cwd=repo_root,
            capture_output=True,
            timeout=30,
        )
    except Exception:
        pass


def main():
    try_startup_update()
    if is_configured():
        run_main_app()
        return

    # Setup mode: start WiFi AP, then web server and show wizard on screen (with QR code)
    start_wifi_ap()
    if not start_setup_server():
        sys.exit(1)
    url = f"http://127.0.0.1:{SETUP_PORT}/setup"
    open_browser(url)
    # Keep launcher alive so server keeps running; when user completes setup they reboot
    try:
        while True:
            time.sleep(60)
            if is_configured():
                break
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
