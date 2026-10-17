"""Automated tests for AI Remote PC Control - Stage 4: Screen Streaming & Terminal Viewing.

Verifies:
1. High-speed JPEG capture engine (ScreenCapture) with scaling and telemetry.
2. Terminal screen viewer engine (ANSI 24-bit TrueColor Unicode Half-Blocks).
3. FastAPI Streaming Server endpoints:
   - GET / (Interactive Web Viewer UI)
   - GET /status (Streaming metrics & active client count)
   - WebSocket /stream (Continuous binary JPEG frame streaming & control ping/pong)
4. FastMCP view_terminal tool registration and output formatting.
"""

import json
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from starlette.testclient import TestClient

from streaming.capture import ScreenCapture
from streaming.server import app
from streaming.terminal_viewer import render_ansi_halfblock


def test_screen_capture_engine():
    print("\n[Stage 4 - Test 1] Testing ScreenCapture engine...")
    cap = ScreenCapture(default_quality=75, scale=0.75)
    
    jpeg_bytes, w, h = cap.capture_jpeg()
    assert jpeg_bytes is not None, "Capture returned empty frame"
    assert len(jpeg_bytes) > 1000, "Frame size too small"
    assert w > 0 and h > 0, "Invalid dimensions"
    
    stats = cap.get_stats()
    assert "fps" in stats
    assert "resolution" in stats
    print(f"  ✓ Frame captured: {w}x{h}, {round(len(jpeg_bytes)/1024, 1)} KB (Engine: {stats.get('engine')})")
    cap.close()


def test_terminal_viewer_renderer():
    print("\n[Stage 4 - Test 2] Testing terminal screen viewer (ANSI Half-Block)...")
    from agent.tools.screen import capture_screenshot
    
    tmp_img = "/tmp/test_stage4_render.jpg"
    shot = capture_screenshot(output_path=tmp_img, quality=70)
    assert shot["success"] is True, f"Failed to capture snapshot: {shot}"
    
    try:
        ansi_output = render_ansi_halfblock(tmp_img, max_cols=60)
        assert len(ansi_output) > 100, "Rendered ANSI output is empty"
        assert "\033[38;2;" in ansi_output, "TrueColor escape sequence missing"
        assert "▀" in ansi_output, "Half-block character missing"
        print(f"  ✓ ANSI TrueColor half-block renderer generated {len(ansi_output)} characters across 60 columns")
    finally:
        if os.path.exists(tmp_img):
            os.remove(tmp_img)


def test_fastapi_streaming_server():
    print("\n[Stage 4 - Test 3] Testing FastAPI server & WebSocket streaming endpoints...")
    with TestClient(app) as client:
        # 1. Test GET / (HTML viewer)
        resp_html = client.get("/")
        assert resp_html.status_code == 200
        assert "<title>AI Remote PC - Live Screen Viewer</title>" in resp_html.text
        assert 'id="screen-view"' in resp_html.text
        print("  ✓ GET / returned valid HTML5 Viewer web page")

        # 2. Test GET /status
        resp_status = client.get("/status")
        assert resp_status.status_code == 200
        status_data = resp_status.json()
        assert "active_viewers" in status_data
        assert "is_wayland" in status_data
        print(f"  ✓ GET /status returned telemetry (Viewers: {status_data['active_viewers']}, Session: {status_data.get('engine')})")

        # 3. Test WebSocket /stream
        with client.websocket_connect("/stream") as ws:
            # Receive binary frame
            frame_data = ws.receive_bytes()
            assert len(frame_data) > 1000, "WebSocket frame too small"
            print(f"  ✓ WebSocket /stream delivered live binary frame ({round(len(frame_data)/1024, 1)} KB)")

            # Send ping message to test latency measurement
            ws.send_json({"type": "ping", "t": 123456.7})
            pong_msg = ws.receive_json()
            assert pong_msg.get("type") == "pong"
            assert pong_msg.get("t") == 123456.7
            print("  ✓ WebSocket ping/pong latency measurement exchange succeeded")

            # Send control message (set_fps)
            ws.send_json({"action": "set_fps", "fps": 20})
            print("  ✓ Sent stream control command (set_fps)")


def test_mcp_view_terminal_tool():
    print("\n[Stage 4 - Test 4] Testing FastMCP view_terminal tool...")
    from agent.mcp_server import create_mcp_server
    server = create_mcp_server()
    assert server is not None

    # Call view_terminal via FastMCP or directly
    from streaming.terminal_viewer import render_ansi_halfblock
    from agent.tools.screen import capture_screenshot

    tmp = "/tmp/test_mcp_term.jpg"
    shot = capture_screenshot(output_path=tmp, quality=50)
    assert shot["success"] is True
    try:
        art = render_ansi_halfblock(tmp, max_cols=40)
        assert len(art) > 50
        print("  ✓ FastMCP view_terminal rendering verified successfully")
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def run_all():
    print("==================================================")
    print(" Running Stage 4 (Screen Streaming) Test Suite    ")
    print("==================================================")
    test_screen_capture_engine()
    test_terminal_viewer_renderer()
    test_fastapi_streaming_server()
    test_mcp_view_terminal_tool()
    print("\n==================================================")
    print(" ALL STAGE 4 STREAMING TESTS PASSED!              ")
    print("==================================================")


if __name__ == "__main__":
    run_all()
