# Nothing starts after reboot / How to enable startup

Automatic update **is** already enabled: the launcher runs `git pull` at the very start when it runs. If **nothing** appears after reboot, the launcher never runs, so nothing (including the update) happens.

Use this checklist to get the launcher starting again. Then the same steps will keep auto-update working (the Pi will pull from GitHub on every boot when it has network).

---

## 1. Check desktop autostart (main way DogPhone starts)

DogPhone is started by a **desktop autostart** entry when you log into the desktop. Your username and path might be different (e.g. `dogphone`, `Dogphone`).

```bash
# Replace dogphone / Dogphone if yours are different
ls -la /home/dogphone/.config/autostart/dogphone.desktop
cat /home/dogphone/.config/autostart/dogphone.desktop
```

You should see something like:

```
Exec=/usr/bin/python3 /home/dogphone/Dogphone/pi/launcher.py
Path=/home/dogphone/Dogphone
```

- **If the file is missing or paths are wrong:** run the install script again from your project folder:
  ```bash
  cd ~/Dogphone
  ./pi/install-image.sh
  ```
  Then reboot.

---

## 2. Check auto-login to desktop

If the Pi shows a **login screen** and nobody logs in, the desktop (and autostart) never run.

```bash
sudo raspi-config
```

Go to: **System Options** → **Boot / Auto Login** → **Desktop Autologin**.  
Finish and reboot.

---

## 3. Only one instance (fix 409 Conflict / port in use)

If you see **Telegram 409 Conflict** or **Port 8766 is in use**, two copies of the app are running (e.g. launcher at boot + you ran `python3 pi/main.py`). Only one must run.

**Before running the app by hand**, stop everything:

```bash
pkill -f "python3.*main.py"
pkill -f "launcher.py"
sleep 2
cd ~/Dogphone
python3 pi/main.py
```

**Normal use:** Don’t run `python3 pi/main.py` yourself. Reboot and let the launcher start the app; use the status page and Test call.

---

## 4. Run the launcher by hand (see why it might fail)

SSH in (or use keyboard and terminal on the Pi) and run:

```bash
cd ~/Dogphone
python3 pi/launcher.py
```

- If you see **ImportError** or **No module named …**: install dependencies:
  ```bash
  pip3 install -r pi/requirements.txt
  ```
- If the **browser opens** and you see the status/setup page: launcher works; the problem is only that it’s not starting at boot (autostart or auto-login).
- Note any **error message** and fix that (e.g. config path, missing Flask, etc.).

---

## 5. Optional: enable systemd fallback

If desktop autostart still doesn’t run the launcher (e.g. different desktop or autostart not firing), you can enable a **systemd** service that starts the launcher after the desktop is up. Run this **once** (adjust paths and user if needed):

```bash
sudo tee /etc/systemd/system/dogphone.service << 'EOF'
[Unit]
Description=DogPhone
After=graphical.target network-online.target
WantedBy=graphical.target

[Service]
Type=simple
User=dogphone
WorkingDirectory=/home/dogphone/Dogphone
Environment=DISPLAY=:0
ExecStartPre=/bin/sleep 15
ExecStart=/usr/bin/python3 /home/dogphone/Dogphone/pi/launcher.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=graphical.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable dogphone
sudo systemctl start dogphone
```

Replace `dogphone` and `/home/dogphone/Dogphone` with your username and path. Then reboot. You can have **both** autostart and this service; only one launcher will run (the other may see the port in use and exit, or you can disable one of them).

---

## 5. Automatic update (reminder)

When the launcher **does** start (by autostart or systemd), it:

1. Runs `git pull origin main` (if the project is a git clone and the Pi has network).
2. Then starts the status/setup page and main app.

So you don’t need to “enable” update separately: **fix startup first**, then push to GitHub and reboot; the Pi will pull the latest on that boot.
