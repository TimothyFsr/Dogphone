# DogPhone – Commercialization Notes

## Why this stack works for a product

- **No backend to run**: Only the Pi and Telegram. No monthly server or database costs.
- **Familiar apps**: Owners use Telegram (or any browser for the call). No custom app required; optional app later can wrap the same flow.
- **Easy setup**: One bot, one chat ID, one config file or wizard. No port forwarding, no DNS, no SSL on the Pi.

## Packaging options

1. **SD card image**: Pre-flash Raspberry Pi OS with DogPhone installed; on first boot the **launcher** shows the setup wizard on screen (QR code + instructions). User plugs in power, connects phone to **DogPhone-Setup** WiFi (password on sticker/box), scans QR, completes Telegram setup. No keyboard or SSH needed.
2. **Sticker / quick start card**: Include a small card or sticker with: WiFi name **DogPhone-Setup**, password (e.g. **dogphone123** or a unique one per unit), and “Scan the QR code on the screen to set up”.
3. **App store / website**: Sell the Pi (or partner with a hardware kit). Download “DogPhone Installer” from your site; it clones the repo and runs `install.sh`; first run of `launcher.py` triggers the on-screen setup.
4. **Optional cloud later**: Add a small backend (e.g. Vercel/Cloudflare) for: device registration, “find my Chat ID” flow, optional OTA updates. The current design does not depend on it.

## Support and setup flow

- **Get Chat ID**: Document “Message your bot, then run `get_chat_id.py`” or offer a “Get my Chat ID” web page that uses the user’s bot token (handled client-side or via your backend) and displays the ID.
- **Troubleshooting**: Checklist: WiFi, bot token, chat ID, VIDEO_CALL_URL (Zoom link) set and opens on phone, /cookie triggers servo. Publish a short FAQ.

## Scaling and variants

- **Multiple dogs/households**: Each device has its own bot (or one bot with multiple chat IDs and a “which device?” flow). Room name per device avoids collisions.
- **White-label**: Room name and Telegram bot are per-customer; no shared backend.
- **Premium features** (if you add a backend later): Multiple users per device, call history, treat schedule, etc.

## Legal and compliance

- **Data**: Video/audio goes through Zoom (user’s Personal Meeting link). Telegram stores only bot messages. No need to store video on your side unless you add recording.
- **Telegram ToS**: Bot usage must comply with Telegram’s terms; current use (notifications + commands) is standard.

## Possible future improvements

- **Mobile app**: Same flow (Telegram + Zoom link), but app can add push notifications, “Join call” button, “Send cookie” button, and optional device management.
- **Different video backends**: VIDEO_CALL_URL can point to Zoom, Whereby, or any meeting URL; the Pi still “opens URL + notifies via Telegram.”
