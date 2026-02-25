#!/usr/bin/env python3
"""
DogPhone launcher: always show a status page first, then run setup or main app.
Run this on boot so you always see something (status with network, Telegram, Test call button).
"""
import os
import subprocess
import sys
import time
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import load_config, VERSION

SETUP_PORT = 8765
STATUS_PORT = 8767
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


def open_standby_screen():
    """Show 'DogPhone ready' on the display (before main app takes over)."""
    standby = Path(__file__).resolve().parent / "standby.html"
    if not standby.exists():
        return
    open_browser(standby.as_uri())


def run_main_app():
    """Run the real DogPhone app (blocking)."""
    open_standby_screen()
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
        subprocess.run(
            ["git", "pull", "origin", "main"],
            cwd=repo_root,
            capture_output=True,
            timeout=30,
        )
    except Exception:
        pass


def get_network_info():
    """Return (ips_str, internet_ok)."""
    ips = []
    try:
        r = subprocess.run(
            ["hostname", "-I"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if r.returncode == 0 and r.stdout:
            ips = r.stdout.strip().split()
    except Exception:
        pass
    ips_str = " ".join(ips) if ips else "—"
    try:
        import urllib.request
        urllib.request.urlopen("https://api.telegram.org", timeout=3)
        return ips_str, True
    except Exception:
        return ips_str, False


def run_status_server():
    """Serve the status page (network, Telegram config, Test call link) on STATUS_PORT."""
    try:
        from flask import Flask
        app = Flask(__name__)
        html_path = Path(__file__).resolve().parent / "status_page.html"

        @app.route("/api/main-up")
        def main_up():
            try:
                import urllib.request
                urllib.request.urlopen(f"http://127.0.0.1:8766/", timeout=2)
                return "1"
            except Exception:
                return "0"

        @app.route("/")
        def status():
            cfg = load_config()
            ips, internet_ok = get_network_info()
            token_ok = bool(cfg.get("telegram_bot_token"))
            chat_ok = bool(cfg.get("telegram_chat_id"))
            token_status = "set" if token_ok else "missing"
            token_class = "ok" if token_ok else "err"
            chat_status = "set" if chat_ok else "missing"
            if chat_ok and cfg.get("telegram_chat_id"):
                chat_status = "set (" + str(cfg["telegram_chat_id"]) + ")"
            chat_class = "ok" if chat_ok else "err"
            internet_status = "yes" if internet_ok else "no"
            internet_class = "ok" if internet_ok else "warn"
            jitsi_room = cfg.get("jitsi_room", "—")
            html = open(html_path).read()
            html = html.replace("{{ version }}", VERSION)
            html = html.replace("{{ network_ips }}", ips or "—")
            html = html.replace("{{ internet_status }}", internet_status)
            html = html.replace("{{ internet_class }}", internet_class)
            html = html.replace("{{ token_status }}", token_status)
            html = html.replace("{{ token_class }}", token_class)
            html = html.replace("{{ chat_status }}", chat_status)
            html = html.replace("{{ chat_class }}", chat_class)
            html = html.replace("{{ jitsi_room }}", jitsi_room)
            return html

        app.run(host="127.0.0.1", port=STATUS_PORT, debug=False, use_reloader=False)
    except Exception as e:
        print("Status server failed:", e, file=sys.stderr)


def main():
    try_startup_update()
    # If status server is already running, another launcher instance is up; exit
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect(("127.0.0.1", STATUS_PORT))
        s.close()
        return
    except Exception:
        pass

    # Always start status server (so status page is available); open the right page
    t = threading.Thread(target=run_status_server, daemon=True)
    t.start()
    time.sleep(1)

    if not is_configured():
        # Setup mode: WiFi AP + setup wizard
        start_wifi_ap()
        if not start_setup_server():
            sys.exit(1)
        open_browser(f"http://127.0.0.1:{SETUP_PORT}/setup")
        try:
            while True:
                time.sleep(60)
                if is_configured():
                    break
        except KeyboardInterrupt:
            pass
        return

    # Configured: show status page (network, Telegram, Test call) and start main in subprocess
    open_browser(f"http://127.0.0.1:{STATUS_PORT}/")
    main_py = Path(__file__).resolve().parent / "main.py"
    subprocess.Popen(
        [sys.executable, str(main_py)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
