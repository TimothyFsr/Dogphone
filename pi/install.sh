#!/bin/bash
# DogPhone – install dependencies and optional systemd service on Raspberry Pi
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

echo "DogPhone install (Raspberry Pi)"
echo "==============================="

# Python 3 venv recommended but not required
if command -v python3 &>/dev/null; then
  PYTHON=python3
else
  PYTHON=python
fi

echo "Using: $PYTHON"
$PYTHON -m pip install --user -r "$SCRIPT_DIR/requirements.txt" 2>/dev/null || true
$PYTHON -m pip install -r "$SCRIPT_DIR/requirements.txt" 2>/dev/null || true

# Config
if [ ! -f "$REPO_ROOT/config/config.env" ]; then
  if [ -f "$REPO_ROOT/config/config.example.env" ]; then
    cp "$REPO_ROOT/config/config.example.env" "$REPO_ROOT/config/config.env"
    echo "Created config/config.env – please edit and set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID"
  fi
fi

# systemd service (optional)
read -p "Install systemd service so DogPhone runs on boot? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[yY] ]]; then
  SERVICE_FILE="/etc/systemd/system/dogphone.service"
  if [ -w "/etc/systemd/system" ] 2>/dev/null; then
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=DogPhone
After=graphical.target network-online.target
WantedBy=graphical.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$REPO_ROOT
Environment=DISPLAY=:0
ExecStart=$PYTHON $SCRIPT_DIR/launcher.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    sudo systemctl daemon-reload
    sudo systemctl enable dogphone
    echo "Service installed. Start now: sudo systemctl start dogphone"
  else
    echo "Cannot write to /etc/systemd/system. Run with sudo or copy pi/dogphone.service manually."
  fi
fi

# Optional: allow reboot without password (for setup wizard "restart when done")
SUDOERS_D="/etc/sudoers.d"
if [ -d "$SUDOERS_D" ] && [ -w "$SUDOERS_D" ] 2>/dev/null; then
  echo ""
  read -p "Allow DogPhone to reboot after setup (passwordless sudo reboot)? [y/N] " -n 1 -r
  echo
  if [[ $REPLY =~ ^[yY] ]]; then
    echo "$USER ALL=(ALL) NOPASSWD: /usr/sbin/reboot" | sudo tee "$SUDOERS_D/99-dogphone-reboot" >/dev/null
    sudo chmod 440 "$SUDOERS_D/99-dogphone-reboot"
    echo "Added sudoers rule for reboot."
  fi
fi

echo ""
echo "Next steps:"
echo "  Consumer setup: run $PYTHON $SCRIPT_DIR/launcher.py – screen shows QR code; connect to DogPhone-Setup WiFi and complete setup on your phone."
echo "  Or manual: edit config/config.env (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID), then run launcher.py or main.py."
echo "  Press the button to call; send /cookie in Telegram to treat."
