# DogPhone

A Raspberry Pi device that lets your dog **call you** with one button press, and lets you **send a treat** remotely (e.g. via Telegram).

Designed to be **easy to set up** and **commercialization-ready**.

---

## How it works

| Feature | How it works |
|--------|----------------|
| **Dog calls you** | Dog presses a big button → Pi opens a **video call room** (Jitsi Meet) and sends you a **Telegram message** with a “Join” link. You tap the link on your phone and see/hear your dog. |
| **You send a treat** | You send **`/cookie`** (or “cookie”) to the DogPhone Telegram bot. The Pi receives it and triggers a **servo** to dispense a treat. |

- **Video/audio**: [Jitsi Meet](https://meet.jit.si) (free, no account needed, works in the phone browser).
- **Notifications + treat command**: **Telegram** (one bot, one chat; no extra backend server).

**Why not Google Meet or Telegram video?** Google Meet is hard to automate from a Pi (no simple “join as device” flow). Telegram’s Bot API cannot start voice/video calls; only the official app can. Jitsi gives a single, stable link you open on your phone with no sign-up. You can switch to a different WebRTC provider later if you prefer.

---

## Hardware

- **Raspberry Pi** (4 recommended; 3B+ may work with lighter usage)
- **Camera** (Pi Camera or USB)
- **Microphone** (USB or Pi compatible)
- **Screen** (HDMI; for showing the call or a “Call mom/dad” UI)
- **Button** (GPIO; default **BCM 17** – connect one side to GPIO 17, other to GND; use internal pull-up)
- **Servo** (GPIO; default **BCM 27** – for treat dispenser; 5 V and GND as needed)

Pin defaults can be changed in `config/config.env` (`BUTTON_GPIO`, `SERVO_GPIO`).

---

## One-time setup (consumer flow – “plug in and follow the screen”)

When someone buys the system, they **plug in power** and the **screen shows simple instructions** with a **QR code**. No SSH, no editing files.

1. **Plug in** the device. The screen turns on and shows:
   - *“Connect your phone to WiFi **DogPhone-Setup**”* (password on the box or sticker, e.g. `dogphone123`).
   - A **QR code** and a URL (e.g. `http://192.168.4.1:8765`).
2. **On your phone**: Connect to WiFi **DogPhone-Setup**, then **scan the QR code** (or open the URL in the browser). The setup page opens on your phone.
3. **Create a Telegram bot**: In Telegram, open **@BotFather**, send `/newbot`, follow the steps, then **copy the bot token** and paste it into the setup page.
4. **Send a message** to your new bot (e.g. “hi”), then on the setup page tap **“I sent a message – detect me”**. The device finds your Chat ID and saves it.
5. The device **restarts automatically**. After that, the dog can press the button to call you, and you can send **/cookie** in Telegram to dispense a treat.

Optional: for automatic reboot after setup, allow the DogPhone user to run `sudo reboot` without a password, e.g. add a file under `/etc/sudoers.d/` (see `pi/install.sh` or docs).

**Nothing starts after reboot?** DogPhone runs from **desktop autostart** (not systemd), so the desktop must be up and auto-login enabled. Run `./pi/install-image.sh` again to install the autostart entry, then reboot. See [docs/IMAGE-BUILD.md](docs/IMAGE-BUILD.md#troubleshooting).

---

## Project layout

```
DogPhone/
├── README.md                 # This file
├── pi/
│   ├── launcher.py           # Entry point: setup wizard vs main app
│   ├── main.py               # Main app: button, Telegram, Jitsi, servo
│   ├── setup_server.py       # Setup web server (wizard + API)
│   ├── setup_wizard.html      # On-screen + phone setup UI (with QR code)
│   ├── start_setup_ap.sh      # WiFi hotspot "DogPhone-Setup" for setup
│   ├── config.py             # Load/save config (env or file)
│   ├── get_chat_id.py        # Optional CLI helper for Chat ID
│   ├── requirements.txt      # Python deps for Pi
│   ├── install.sh            # Interactive install (dev or one-off)
│   ├── install-image.sh      # Non-interactive install for ship-ready image
│   ├── dogphone.desktop      # Autostart entry (runs launcher when desktop loads)
│   └── dogphone.service      # Optional systemd unit (display usually needs autostart)
├── config/
│   └── config.example.env    # Example env for Pi
└── docs/
    └── COMMERCIALIZATION.md  # Packaging, support, scaling notes
```

---

## Installing for shipping (flash once, ship to clients)

**You** build one SD card image; **clients** only plug in and follow the on-screen QR setup. No install steps for them.

1. Flash **Raspberry Pi OS (desktop)** and enable **auto-login to desktop**.
2. Copy the DogPhone project to `/home/pi/DogPhone` on the Pi.
3. Run **`./pi/install-image.sh`** (non-interactive; installs deps and enables DogPhone on boot; does *not* create config so first boot = setup wizard).
4. Reboot and confirm the **setup screen with QR code** appears.
5. Create a **golden image** of the SD card (e.g. `dd` or Win32 Disk Imager).
6. Flash that image to every unit you ship. Include a **sticker** with WiFi **DogPhone-Setup** and the password (e.g. `dogphone123`).

Full step-by-step: **[docs/IMAGE-BUILD.md](docs/IMAGE-BUILD.md)**.

---

## Quick start (developer)

1. On the Pi, clone or copy this repo.
2. Install: `./pi/install.sh`. For **consumer-style setup**: don’t create `config.env`; on first boot run `python pi/launcher.py` — the screen shows the setup wizard with QR code; connect to **DogPhone-Setup** WiFi and complete setup on your phone. For **fast dev setup**: copy `config/config.example.env` to `config/config.env` and set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`, then run `python pi/launcher.py` or `python pi/main.py`.
3. Press the button → you get a Telegram message with the Jitsi link. Send `/cookie` to the bot → servo runs.

---

## Commercialization

- **No custom backend**: Only the Pi and Telegram; no server to host or pay for.
- **Easy setup**: Single wizard or config page (bot token + chat id + optional room name).
- **Scalable**: Each device is independent; you can later add an optional cloud dashboard (e.g. device registration, OTA) without changing the core flow.
- See `docs/COMMERCIALIZATION.md` for packaging, support, and scaling ideas.

---

## License

Use and modify as needed for personal or commercial use.
