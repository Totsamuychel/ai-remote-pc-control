#!/usr/bin/env python3
"""FastAPI Real-Time Screen Streaming Server via WebSockets.

Streams desktop frames as compressed JPEG binaries to web clients and viewers,
providing real-time telemetry (FPS, resolution, network latency, bandwidth).
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Set

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse

from streaming.capture import ScreenCapture

app = FastAPI(title="AI Remote PC - Screen Streaming Service", version="0.1.0")

# Global capture engine and client connection registry
capture_engine = ScreenCapture(default_quality=70, scale=0.8)
active_clients: Set[WebSocket] = set()

VIEWER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Remote PC - Live Screen Viewer</title>
    <style>
        :root {
            --bg-color: #0f172a;
            --panel-bg: #1e293b;
            --panel-border: #334155;
            --accent: #38bdf8;
            --accent-hover: #0284c7;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --success: #22c55e;
            --danger: #ef4444;
            --warning: #f59e0b;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background: var(--bg-color); color: var(--text-main); display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
        
        header {
            background: var(--panel-bg);
            border-bottom: 1px solid var(--panel-border);
            padding: 10px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
        }
        .logo-area { display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 1.1rem; }
        .logo-badge { background: var(--accent); color: #000; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }
        
        .hud-stats { display: flex; align-items: center; gap: 16px; font-size: 0.85rem; }
        .hud-item { display: flex; align-items: center; gap: 6px; }
        .hud-item span { color: var(--text-muted); }
        .hud-item strong { color: var(--text-main); font-weight: 600; }
        .status-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--danger); display: inline-block; }
        .status-dot.connected { background: var(--success); box-shadow: 0 0 8px var(--success); }
        .status-dot.paused { background: var(--warning); }

        .controls { display: flex; align-items: center; gap: 10px; }
        button, select {
            background: var(--panel-bg);
            color: var(--text-main);
            border: 1px solid var(--panel-border);
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 0.85rem;
            cursor: pointer;
            transition: all 0.15s ease;
        }
        button:hover { background: var(--panel-border); }
        button.primary { background: var(--accent); color: #000; border-color: var(--accent); font-weight: 600; }
        button.primary:hover { background: var(--accent-hover); }

        main {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 12px;
            background: #020617;
            position: relative;
        }
        #screen-view {
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
            border-radius: 6px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            background: #000;
        }
        .placeholder-text {
            position: absolute;
            color: var(--text-muted);
            font-size: 1.2rem;
            text-align: center;
            pointer-events: none;
        }
    </style>
</head>
<body>
    <header>
        <div class="logo-area">
            <span>AI Remote PC</span>
            <span class="logo-badge">LIVE STREAM</span>
        </div>

        <div class="hud-stats">
            <div class="hud-item">
                <span id="conn-indicator" class="status-dot"></span>
                <strong id="conn-status">Disconnected</strong>
            </div>
            <div class="hud-item">
                <span>FPS:</span>
                <strong id="stat-fps">0.0</strong>
            </div>
            <div class="hud-item">
                <span>Res:</span>
                <strong id="stat-res">-</strong>
            </div>
            <div class="hud-item">
                <span>Latency:</span>
                <strong id="stat-latency">0 ms</strong>
            </div>
            <div class="hud-item">
                <span>Rate:</span>
                <strong id="stat-rate">0 KB/s</strong>
            </div>
        </div>

        <div class="controls">
            <label for="fps-select" style="font-size: 0.8rem; color: var(--text-muted);">Target FPS:</label>
            <select id="fps-select">
                <option value="5">5 FPS</option>
                <option value="10">10 FPS</option>
                <option value="15" selected>15 FPS</option>
                <option value="25">25 FPS</option>
                <option value="30">30 FPS</option>
            </select>
            <button id="btn-toggle" class="primary">Start Stream</button>
            <button id="btn-fullscreen">Fullscreen</button>
        </div>
    </header>

    <main id="player-container">
        <img id="screen-view" alt="Remote Desktop Feed" style="display: none;" />
        <div id="placeholder" class="placeholder-text">
            Desktop stream is offline.<br/>Click <strong>Start Stream</strong> to begin.
        </div>
    </main>

    <script>
        let ws = null;
        let isStreaming = false;
        let lastFrameTime = performance.now();
        let frameCount = 0;
        let bytesReceived = 0;
        let lastStatTime = performance.now();
        let pingInterval = null;

        const imgEl = document.getElementById('screen-view');
        const placeholderEl = document.getElementById('placeholder');
        const btnToggle = document.getElementById('btn-toggle');
        const btnFullscreen = document.getElementById('btn-fullscreen');
        const fpsSelect = document.getElementById('fps-select');
        const connStatus = document.getElementById('conn-status');
        const connIndicator = document.getElementById('conn-indicator');
        const statFps = document.getElementById('stat-fps');
        const statRes = document.getElementById('stat-res');
        const statLatency = document.getElementById('stat-latency');
        const statRate = document.getElementById('stat-rate');

        function startStream() {
            if (ws) {
                ws.close();
            }

            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/stream`;

            connStatus.innerText = 'Connecting...';
            connIndicator.className = 'status-dot paused';

            ws = new WebSocket(wsUrl);
            ws.binaryType = 'blob';

            ws.onopen = () => {
                isStreaming = true;
                connStatus.innerText = 'Live';
                connIndicator.className = 'status-dot connected';
                btnToggle.innerText = 'Stop Stream';
                btnToggle.style.background = '#ef4444';
                placeholderEl.style.display = 'none';
                imgEl.style.display = 'block';

                // Send target FPS setting
                sendControl({ action: 'set_fps', fps: parseInt(fpsSelect.value) });

                // Latency ping loop
                pingInterval = setInterval(() => {
                    if (ws && ws.readyState === WebSocket.OPEN) {
                        ws.send(JSON.stringify({ type: 'ping', t: performance.now() }));
                    }
                }, 1000);
            };

            ws.onmessage = (event) => {
                if (typeof event.data === 'string') {
                    try {
                        const msg = JSON.parse(event.data);
                        if (msg.type === 'pong') {
                            const rtt = Math.round(performance.now() - msg.t);
                            statLatency.innerText = `${rtt} ms`;
                        }
                    } catch (e) {}
                    return;
                }

                // Handle binary JPEG frame
                const blob = event.data;
                bytesReceived += blob.size;
                frameCount++;

                const url = URL.createObjectURL(blob);
                imgEl.onload = () => {
                    URL.revokeObjectURL(url);
                    statRes.innerText = `${imgEl.naturalWidth}x${imgEl.naturalHeight}`;
                };
                imgEl.src = url;

                // Calculate metrics every second
                const now = performance.now();
                const elapsed = (now - lastStatTime) / 1000;
                if (elapsed >= 1.0) {
                    const currentFps = (frameCount / elapsed).toFixed(1);
                    const kbRate = (bytesReceived / 1024 / elapsed).toFixed(1);
                    statFps.innerText = currentFps;
                    statRate.innerText = `${kbRate} KB/s`;
                    frameCount = 0;
                    bytesReceived = 0;
                    lastStatTime = now;
                }
            };

            ws.onclose = () => {
                isStreaming = false;
                connStatus.innerText = 'Disconnected';
                connIndicator.className = 'status-dot';
                btnToggle.innerText = 'Start Stream';
                btnToggle.style.background = '';
                placeholderEl.style.display = 'block';
                if (pingInterval) clearInterval(pingInterval);
            };

            ws.onerror = (err) => {
                console.error('WebSocket Error:', err);
                ws.close();
            };
        }

        function stopStream() {
            if (ws) {
                ws.close();
                ws = null;
            }
        }

        function sendControl(data) {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify(data));
            }
        }

        btnToggle.addEventListener('click', () => {
            if (isStreaming) {
                stopStream();
            } else {
                startStream();
            }
        });

        fpsSelect.addEventListener('change', () => {
            sendControl({ action: 'set_fps', fps: parseInt(fpsSelect.value) });
        });

        btnFullscreen.addEventListener('click', () => {
            if (!document.fullscreenElement) {
                document.getElementById('player-container').requestFullscreen().catch(err => {
                    alert(`Error attempting to enable fullscreen: ${err.message}`);
                });
            } else {
                document.exitFullscreen();
            }
        });
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def get_viewer_page():
    """Serve the real-time screen stream viewer web page."""
    return HTMLResponse(content=VIEWER_HTML)


@app.get("/status")
async def get_streaming_status():
    """Return streaming service telemetry and connected client count."""
    stats = capture_engine.get_stats()
    stats["active_viewers"] = len(active_clients)
    stats["server_time"] = time.time()
    return JSONResponse(content=stats)


@app.websocket("/stream")
async def websocket_stream_endpoint(websocket: WebSocket):
    """Real-time desktop streaming WebSocket endpoint.

    Continuously sends compressed JPEG binary frames to client at target FPS,
    while processing client control commands (set_fps, set_quality, ping/pong).
    """
    await websocket.accept()
    active_clients.add(websocket)

    target_fps = 15
    quality = 70
    scale = 0.8
    is_paused = False

    async def client_message_listener():
        """Listen for client control messages in background task."""
        nonlocal target_fps, quality, scale, is_paused
        try:
            while True:
                text_msg = await websocket.receive_text()
                try:
                    data = json.loads(text_msg)
                    msg_type = data.get("type")
                    if msg_type == "ping":
                        await websocket.send_text(json.dumps({"type": "pong", "t": data.get("t")}))
                    elif data.get("action") == "set_fps":
                        target_fps = max(1, min(30, int(data.get("fps", 15))))
                    elif data.get("action") == "set_quality":
                        quality = max(20, min(95, int(data.get("quality", 70))))
                    elif data.get("action") == "pause":
                        is_paused = True
                    elif data.get("action") == "resume":
                        is_paused = False
                except json.JSONDecodeError:
                    pass
        except WebSocketDisconnect:
            pass
        except Exception:
            pass

    listener_task = asyncio.create_task(client_message_listener())

    try:
        while True:
            if is_paused:
                await asyncio.sleep(0.1)
                continue

            t0 = time.time()
            frame_delay = 1.0 / max(1, target_fps)

            # Capture frame in threadpool to keep event loop responsive
            loop = asyncio.get_running_loop()
            jpeg_bytes, w, h = await loop.run_in_executor(
                None, capture_engine.capture_jpeg, quality, scale
            )

            if jpeg_bytes:
                await websocket.send_bytes(jpeg_bytes)

            elapsed = time.time() - t0
            sleep_duration = max(0.005, frame_delay - elapsed)
            await asyncio.sleep(sleep_duration)

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        listener_task.cancel()
        active_clients.discard(websocket)


def main():
    import uvicorn

    parser = argparse.ArgumentParser(description="AI Remote PC - Screen Streaming Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host address to bind")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    args = parser.parse_args()

    print(f"Starting Screen Streaming Server on http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
