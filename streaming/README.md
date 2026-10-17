# Screen Streaming Module — Stage 4

This module is planned for implementation in **Stage 4**.

## Planned Architecture & Components:
1. `server.py` — FastAPI service with `/stream` WebSocket endpoint.
2. `capture.py` — Fast screen frame capture using `mss` and JPEG compression via `Pillow`.
3. `requirements.txt` — Dependencies: `fastapi`, `uvicorn`, `mss`, `Pillow`, `websockets`.
4. Web-based lightweight screen viewer with real-time frame rendering.
