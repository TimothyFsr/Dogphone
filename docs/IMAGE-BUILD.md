# Building a ship-ready DogPhone image

This guide is for **you** (the manufacturer). You build **one** SD card image; then you duplicate that card (or image file) for every unit you ship. **Clients** only plug in power and follow the on-screen QR setup—they never run install scripts or SSH.

---

## What you need

- A Raspberry Pi (same model you’ll ship, e.g. Pi 4) with SD card
- Monitor + keyboard (or SSH if you set it up headless)
- Network (for apt and pip)

If you set a **custom username** in the Imager (instead of `pi`), edit `install-image.sh` and the service file: replace `User=pi` and paths `/home/pi/DogPhone` with your username and path.

---

## Step 1: Flash Raspberry Pi OS

1. Use **[Raspberry Pi Imager](https://www.raspberrypi.com/software/)** (or Etcher + an OS image).
2. Choose **Raspberry Pi OS** (the **full** desktop version so Chromium and a display are available).
3. Before writing, click the **gear** to set:
   - **Hostname**: e.g. `dogphone`
   - **Enable SSH**: if you want to finish setup over SSH
   - **Set username and password**: e.g. user `pi`, set a password
   - **Configure WiFi** (optional): only if you need internet during this build; leave blank if you’ll use Ethernet
4. Write the image to the SD card, insert it into the Pi, and boot.

---

## Step 2: Boot and prepare the system

1. Log in (at the desktop or over SSH).
2. **Enable auto-login to desktop** (so the display is on and `DISPLAY=:0` works when DogPhone starts):
   - Run: `sudo raspi-config`
   - **System Options** → **Boot / Auto Login** → **Desktop Autologin**
   - Finish and reboot if needed.
3. (Optional) Set WiFi country so the hotspot works later: **Localisation Options** → **Wifi** → choose your country.

---

## Step 3: Install DogPhone (non-interactive)

Put the DogPhone files on the Pi in a fixed location. Two options:

**Option A – Clone from git (if you use a repo):**

```bash
cd /home/pi
git clone https://github.com/YOUR_ORG/DogPhone.git
cd DogPhone
```

**Option B – Copy from your computer (e.g. with SCP or a USB stick):**

Copy the whole `DogPhone` folder to `/home/pi/DogPhone` so the layout is:

```
/home/pi/DogPhone/
├── pi/
│   ├── launcher.py
│   ├── main.py
│   ├── setup_server.py
│   ├── setup_wizard.html
│   ├── start_setup_ap.sh
│   ├── config.py
│   ├── get_chat_id.py
│   ├── requirements.txt
│   ├── install-image.sh   ← used in next step
│   └── dogphone.service
├── config/
│   └── config.example.env
└── ...
```

Then run the **image-build** install script (no prompts; ready for cloning the SD card):

```bash
cd /home/pi/DogPhone
chmod +x pi/install-image.sh
./pi/install-image.sh
```

This script will:

- Install Python dependencies (Flask, python-telegram-bot, requests, RPi.GPIO).
- **Not** create `config/config.env` (so the first boot on the client’s side goes into **setup mode** with the QR code).
- Install a **desktop autostart** entry so DogPhone runs when the desktop loads (this way it has a real display and the browser can open; systemd services often cannot).
- Allow the `pi` user to run `sudo reboot` without a password (so “Setup complete” can restart the device).

---

## Step 4: Make the script executable and test once

```bash
chmod +x /home/pi/DogPhone/pi/start_setup_ap.sh
```

Reboot and confirm:

- The Pi boots to the desktop.
- After a short delay, the **setup wizard** appears on the screen (QR code and “Connect to DogPhone-Setup”).
- If you connect your phone to **DogPhone-Setup** WiFi and scan the QR code, the setup page opens on the phone.

If that works, the image is ready to ship.

---

## Step 5: Create the “golden” image for shipping

1. **Shut down the Pi** (e.g. `sudo shutdown -h now`).
2. Remove the SD card and put it in a reader on your computer.
3. **Create an image** of the card:
   - **macOS/Linux**: e.g. `sudo dd if=/dev/sdX of=dogphone-image.img bs=4M status=progress` (replace `sdX` with the actual device).
   - **Windows**: use a tool like **Win32 Disk Imager** (read to a file).
   - Or use **Raspberry Pi Imager** “Custom” if it supports writing from an existing image.
4. Store `dogphone-image.img` (or the same file under a different name). This is your **golden image**.

---

## Step 6: Ship to clients

- **Flash each unit**: Write the golden image to a new SD card (Raspberry Pi Imager “Use custom”, or Etcher, or `dd`).
- **Optional**: Use a different WiFi password per batch by setting it before imaging (see below).
- **In the box**: Include a small card or sticker with:
  - **WiFi name:** DogPhone-Setup  
  - **Password:** (e.g. `dogphone123`, or your chosen password)  
  - **Instructions:** “Plug in the device. Connect your phone to WiFi **DogPhone-Setup**, then scan the QR code on the screen.”

Clients plug in power → see the setup screen → connect to DogPhone-Setup → scan QR → complete Telegram setup on their phone → device reboots and is ready to use.

---

## Optional: Change the setup WiFi password

Before you create the golden image, you can set a custom password for **DogPhone-Setup**:

```bash
echo 'DOGPHONE_AP_PASSWORD=YourSecurePassword' | sudo tee -a /etc/environment
# Or edit /home/pi/DogPhone/pi/start_setup_ap.sh and set PASSPHRASE=...
```

Then put that same password on the sticker you ship. If you use `/etc/environment`, ensure `start_setup_ap.sh` (or the launcher) reads it when starting the hotspot.

---

## Troubleshooting

### Nothing starts after reboot

DogPhone is started by **desktop autostart** (not systemd), so it only runs after the **desktop** is up and the `pi` user is logged in.

1. **Check that autostart is installed:**
   ```bash
   ls -la /home/pi/.config/autostart/dogphone.desktop
   ```
   If missing, run `./pi/install-image.sh` again.

2. **Run the launcher by hand** (with the desktop already open) to see any errors:
   ```bash
   cd /home/pi/DogPhone
   python3 pi/launcher.py
   ```
   You should see the setup page in Chromium. If you get “No module named …”, install deps: `pip3 install -r pi/requirements.txt`. If the browser doesn’t open, try: `chromium-browser http://127.0.0.1:8765/setup`.

3. **Auto-login must be enabled** so the desktop (and thus autostart) runs without anyone logging in:
   ```bash
   sudo raspi-config
   # System Options → Boot / Auto Login → Desktop Autologin
   ```

4. **If you previously used the systemd service**, disable it so only autostart runs:
   ```bash
   sudo systemctl disable dogphone
   sudo systemctl stop dogphone
   ```
   Then reboot.

### "Unlock keyring" or "Authentication required" on startup

With **auto-login**, the desktop starts without a password, so the **GNOME keyring** stays locked and can show an "Unlock keyring" / "Authentication required" dialog when Chromium starts.

**Fix (do once, with keyboard and screen):**

1. When the dialog appears, enter your **user password** (for `dogphone` or `pi`) to unlock for this session.
2. Open **Passwords and Keys**. If you don’t have it, install and run:  
   `sudo apt install seahorse`  
   then run:  
   `seahorse`  
   (Or from the menu: **Accessories → Passwords and Keys**.)
3. Right-click **Login** (or **Default** keyring) → **Change Password**.
4. Enter your current password, then set the **new password to empty** (leave blank) and confirm.
5. Accept the warning. After that, auto-login will no longer show the keyring prompt.

**Alternative (no GUI):** Remove the keyring so it’s recreated without a password (any passwords stored in the keyring will be lost):  
`rm -f ~/.local/share/keyrings/login.keyring` then reboot. On first login you may be asked to set a keyring password — choose **empty** if offered.

**When building the image:** Do this once on your build Pi before creating the golden image, so shipped units never see the prompt.

### Other issues

| Problem | What to check |
|--------|----------------|
| “DogPhone-Setup” WiFi doesn’t appear | WiFi country set in raspi-config? Run `./pi/start_setup_ap.sh` by hand and check `nmcli`. |
| Client completes setup but device doesn’t reboot | Sudoers rule for `reboot` installed? Check `/etc/sudoers.d/99-dogphone-reboot`. |
| After setup, button doesn’t call | Config saved in `config/config.env`? Launcher runs `main.py` when configured. |

---

## Summary

1. Flash **Raspberry Pi OS (desktop)** and set hostname/SSH/auto-login.
2. Copy or clone **DogPhone** to `/home/pi/DogPhone`.
3. Run **`./pi/install-image.sh`** (non-interactive).
4. Reboot and confirm the **setup wizard with QR code** appears.
5. Create a **golden image** of the SD card and use it for every unit you ship.
6. Ship with a **sticker** (WiFi name + password) so clients can connect and scan the QR code.

After that, clients only **plug in and follow the screen**; no install steps for them.
