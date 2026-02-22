#!/bin/bash
# Start WiFi access point "DogPhone-Setup" so the user can connect their phone.
# Run this when in setup mode (e.g. from launcher or a systemd service).
# Requires: Raspberry Pi OS with NetworkManager (Bookworm default).

set -e
SSID="${DOGPHONE_AP_SSID:-DogPhone-Setup}"
PASSPHRASE="${DOGPHONE_AP_PASSWORD:-dogphone123}"

if ! command -v nmcli &>/dev/null; then
  echo "nmcli not found. Install NetworkManager or use create_ap." >&2
  exit 1
fi

# Find WiFi device
IFACE=$(nmcli -t -f DEVICE,TYPE device | awk -F: '$2=="wifi" {print $1; exit}')
if [ -z "$IFACE" ]; then
  echo "No WiFi device found." >&2
  exit 1
fi

# Create hotspot (Raspberry Pi OS Bookworm)
# If already connected to a network, this may change connectivity.
nmcli device wifi hotspot ifname "$IFACE" ssid "$SSID" password "$PASSPHRASE"
echo "Hotspot started: $SSID (password: $PASSPHRASE)"
echo "Connect your phone to $SSID, then open http://192.168.4.1:8765 or scan the QR code on the screen."
