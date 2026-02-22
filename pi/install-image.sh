#!/bin/bash
# DogPhone – non-interactive install for building a ship-ready SD image.
# Run this once on a Pi; then create an image of the SD card and flash that for every unit you ship.
# Do NOT create config.env so the first boot for the client shows the setup wizard (QR code).
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

PYTHON=python3
[ -z "$(command -v python3)" ] && PYTHON=python

echo "DogPhone image install (non-interactive)"
echo "========================================="

# Dependencies
$PYTHON -m pip install --user -r "$SCRIPT_DIR/requirements.txt" 2>/dev/null || true
$PYTHON -m pip install -r "$SCRIPT_DIR/requirements.txt" 2>/dev/null || true

# Do NOT create config.env – first boot must show setup wizard
# (Remove existing config if you're re-running on a dev Pi and want to test setup again.)
if [ -f "$REPO_ROOT/config/config.env" ]; then
  echo "Note: config/config.env exists; delete it to test setup wizard on next boot."
fi

# systemd service: start after desktop so DISPLAY=:0 exists
SERVICE_FILE="/etc/systemd/system/dogphone.service"
sudo tee "$SERVICE_FILE" >/dev/null << EOF
[Unit]
Description=DogPhone – dog call and treat device
After=graphical.target network-online.target
WantedBy=graphical.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/DogPhone
Environment=DISPLAY=:0
ExecStart=/usr/bin/python3 /home/pi/DogPhone/pi/launcher.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=graphical.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable dogphone
echo "Enabled dogphone.service (runs launcher.py on boot)."

# Allow reboot after setup (no password)
echo "pi ALL=(ALL) NOPASSWD: /usr/sbin/reboot" | sudo tee /etc/sudoers.d/99-dogphone-reboot >/dev/null
sudo chmod 440 /etc/sudoers.d/99-dogphone-reboot
echo "Added sudoers rule for reboot after setup."

# Make AP script executable
chmod +x "$SCRIPT_DIR/start_setup_ap.sh" 2>/dev/null || true

echo ""
echo "Image install done. Reboot to test. On first boot (no config) the setup wizard with QR code will appear."
echo "Create an image of this SD card to ship to clients."
