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

# Run launcher from desktop autostart (so it has a real X session and the browser can open).
# systemd services often cannot open windows on the Pi display.
# Use current user and repo path so it works for any username (pi, dogphone, etc.).
CURRENT_USER="${SUDO_USER:-$USER}"
USER_HOME=$(eval echo "~$CURRENT_USER")
AUTOSTART_DIR="$USER_HOME/.config/autostart"
mkdir -p "$AUTOSTART_DIR"
LAUNCHER_PATH="$REPO_ROOT/pi/launcher.py"
cat > "$AUTOSTART_DIR/dogphone.desktop" << EOF
[Desktop Entry]
Type=Application
Name=DogPhone
Comment=DogPhone launcher (setup or call app)
Exec=/usr/bin/python3 $LAUNCHER_PATH
Path=$REPO_ROOT
Terminal=false
X-GNOME-Autostart-enabled=true
EOF
chown -R "$CURRENT_USER:$CURRENT_USER" "$AUTOSTART_DIR" 2>/dev/null || true
# Disable systemd so only ONE launcher runs (autostart). Two starters = two main.py = Telegram 409 + port in use.
sudo systemctl disable dogphone 2>/dev/null || true
sudo systemctl stop dogphone 2>/dev/null || true
echo "Installed autostart: DogPhone runs when the desktop loads (only one instance)."

# Optional: also enable systemd so it can restart the app if it crashes (runs in background;
# the visible browser is started by the autostart process). Disabled by default to avoid
# two launcher instances. Uncomment below if you prefer systemd-only.
# SERVICE_FILE="/etc/systemd/system/dogphone.service"
# sudo tee "$SERVICE_FILE" >/dev/null << 'SVCEOF'
# [Unit]
# Description=DogPhone
# After=graphical.target network-online.target
# [Service]
# Type=simple
# User=pi
# WorkingDirectory=/home/pi/DogPhone
# Environment=DISPLAY=:0
# ExecStart=/usr/bin/python3 /home/pi/DogPhone/pi/launcher.py
# Restart=on-failure
# RestartSec=10
# [Install]
# WantedBy=graphical.target
# SVCEOF
# sudo systemctl daemon-reload
# sudo systemctl enable dogphone

# Allow reboot after setup (no password)
CURRENT_USER="${SUDO_USER:-$USER}"
echo "$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/sbin/reboot" | sudo tee /etc/sudoers.d/99-dogphone-reboot >/dev/null
sudo chmod 440 /etc/sudoers.d/99-dogphone-reboot
echo "Added sudoers rule for reboot after setup."

# Make AP script executable
chmod +x "$SCRIPT_DIR/start_setup_ap.sh" 2>/dev/null || true

echo ""
echo "Image install done. Reboot to test. On first boot (no config) the setup wizard with QR code will appear."
echo "Create an image of this SD card to ship to clients."
