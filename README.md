# Smooth Stomp v1.0.0 — GOWALK Interactive Game

Local event game for the Skechers Smooth Stomp activation.

## Run locally
1. Install dependencies: `python3 -m pip install -r requirements.txt`
2. Run: `python3 server.py --port 8765`
3. Open: `http://127.0.0.1:8765/`

Or on macOS, double-click `Start Smooth Stomp.command`.

## Current flow
Camera permission → half-body detection → raise hand → READY 3/2/1/GO → 40-second gameplay → 10-second product showcase → result → auto photo → ranking → attract.

## Controls
- `Space`: skip the current scene for testing.
- `O`: open/close config.
- Gameplay config includes BODY/FEET collision, hit radius, item size, max active items, and draggable Z1–Z6 positions.
- Config is stored in `config/zones.json`.

## Local registration/dashboard
- `/register.html`: player registration.
- `/dashboard.html`: staff dashboard.
- Registration data is created locally in `data/registrations.sqlite3`.
- Runtime database files are ignored by Git.

## Camera / pose
The game uses the browser webcam. MediaPipe assets are loaded at runtime, so pose tracking still needs internet access in this build.

## Version
See `VERSION` and `CHANGELOG.md`.
