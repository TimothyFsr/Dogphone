# Updating DogPhone on the Pi without SSH

Use one of these when the Pi is not on your network (e.g. it’s in hotspot mode or WiFi isn’t set up).

---

## Option 1: SD card on your computer (no Pi needed)

1. **Power off the Pi** and remove the SD card.
2. **Insert the SD card** into your Mac or PC (built-in slot or USB adapter).
3. **Open the card** in the file manager. You may see one or two volumes:
   - **boot** (or **bootfs**) – small, FAT32. This is *not* where the app lives.
   - **rootfs** or the **main partition** – this has `home`, `usr`, etc. The app is in `home/<username>/Dogphone` (e.g. `home/dogphone/Dogphone`).
4. **If you don’t see the main partition** (common on Mac because it’s ext4):
   - **Mac:** Install an ext4 driver (e.g. [Paragon ExtFS](https://www.paragon-software.com/home/extfs-mac/) or similar), or use another computer with Linux.
   - **Windows:** Use [Linux File Systems for Windows](https://www.paragon-software.com/home/linuxfs-windows/) or WSL to read ext4, or use a Linux PC.
   - **Linux:** Mount the second partition (e.g. `sudo mount /dev/sdb2 /mnt`) and browse to `/mnt/home/dogphone/Dogphone`.
5. **Copy the updated DogPhone files** from your computer over the existing ones:
   - Replace the contents of `pi/` (e.g. `launcher.py`, `setup_server.py`, `setup_wizard.html`, etc.).
   - Replace `config/config.example.env` if you changed it. Do **not** overwrite `config/config.env` if the device is already set up (that holds the token and chat ID).
6. **Eject the SD card** safely, put it back in the Pi, and power on.

---

## Option 2: USB stick (Pi has keyboard + screen)

1. **Copy the latest DogPhone folder** (or a zip of it) onto a USB stick on your computer.
2. **Plug the USB stick** into the Pi and power on (or plug in while it’s running).
3. **On the Pi:** The stick often appears on the desktop or in the file manager. Open it.
4. **Copy the updated files** into the existing project folder:
   - Open the USB, then open **File Manager** and go to **Home** → **Dogphone** (or your project folder).
   - Copy the **pi** folder from the USB over the existing **pi** folder (replace files when asked). Copy **config/config.example.env** if needed. Do **not** replace **config/config.env** if the device is already configured.
5. **Or use the terminal** (if the USB is at `/media/dogphone/USBNAME`):
   ```bash
   cp -r /media/dogphone/USBNAME/pi/* /home/dogphone/Dogphone/pi/
   ```
   (Adjust USBNAME and paths if your username or folder name differ.)
6. **Safely eject the USB** and reboot the Pi if you want: **Menu → Shutdown → Reboot**.

---

## Option 3: Temporarily put the Pi on WiFi, then SSH

If you can connect the Pi to a monitor and keyboard:

1. **Connect to the hotspot** from your phone and open the setup page (e.g. http://10.42.0.1:8765).
2. If the wizard has a **WiFi step**, enter your home WiFi SSID and password so the Pi joins your network. Then you can SSH from your computer.
3. **Or** on the Pi desktop: click the WiFi icon, select your network, enter the password. Note the Pi’s IP (e.g. **Menu → Preferences → Raspberry Pi Configuration** or run `hostname -I` in a terminal).
4. From your computer: `ssh dogphone@<pi-ip>` (use your username and the IP).
5. Update the app (e.g. `cd Dogphone && git pull` or copy files via `scp`), then disconnect. You can leave WiFi as-is or switch back to hotspot-only later.

---

## Summary

| Method              | Pi needed? | Network? | Best when                          |
|---------------------|------------|----------|------------------------------------|
| **SD card**         | No         | No       | You can remove the card easily     |
| **USB stick**       | Yes (KB+screen) | No  | Pi is already at your desk         |
| **WiFi + SSH**      | Yes (KB+screen) | Yes (after WiFi set) | You want to keep using SSH for updates |

After updating, **do not** overwrite `config/config.env` if the device is already set up; that file holds the Telegram token and Chat ID.
