# Changelog

## v1.0.2 — Camera Gate Fix
- Fixed the setup/camera permission screen staying visible after the game had already advanced.
- Root cause: the `#setup` CSS forced `display:flex` even after its `active` class was removed.
- Setup screen now appears only while `#setup.active` is present.

## v1.0.1 — Web Play
- Added a self-contained web-playable build.
- Webcam runs directly in the browser over HTTPS.
- MediaPipe Pose Landmarker is loaded from CDN for half-body / raised-hand start and BODY collision.
- Includes READY countdown, 40-second gameplay, 6 fixed zones, CONFIG (O), 10-second showcase, result, auto photo, and localStorage ranking.
- Mouse/touch collision and Spacebar scene skip are available as test fallbacks.
- Web version saves ranking locally in the current browser.

## v1.0.0 — GOWALK Interactive Game
- Initial GitHub version of Smooth Stomp.
- GOWALK visual theme.
- Webcam / pose start flow, gameplay, showcase, result, auto photo, ranking.
- Local registration server, dashboard, QR registration, zone config.
