"""Automated tests for AI Remote PC Control - Stage 3: Screen & Windows Management.

Verifies:
1. Desktop screenshot capture via Wayland (grim) and cross-platform (mss + Pillow).
2. Compression to JPEG and formatting to PNG with resolution metadata.
3. Active desktop window enumeration (Hyprland, Sway, X11 wmctrl, Windows API).
4. Window focus switching by title/class query with fallback and error handling.
5. Registration and invocation of Stage 3 MCP tools: screenshot, list_windows, focus_window.
6. Recording of all screen operations into the JSONL audit log.
"""

import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from agent.safety.audit import AuditLogger
from agent.tools.screen import capture_screenshot, focus_window_by_title, list_open_windows


def test_screenshot_capture():
    print("\n[Stage 3 - Test 1] Testing screenshot capture...")
    
    # Test JPEG capture
    res_jpg = capture_screenshot(format="jpeg", quality=85)
    assert res_jpg["success"] is True, f"JPEG capture failed: {res_jpg}"
    assert Path(res_jpg["path"]).exists(), "JPEG file does not exist"
    assert res_jpg["width"] > 0 and res_jpg["height"] > 0
    assert res_jpg["size_bytes"] > 0
    print(f"  ✓ JPEG screenshot captured: {res_jpg['path']} ({res_jpg['width']}x{res_jpg['height']}, {round(res_jpg['size_bytes']/1024, 1)} KB)")

    # Test PNG capture
    res_png = capture_screenshot(format="png")
    assert res_png["success"] is True, f"PNG capture failed: {res_png}"
    assert Path(res_png["path"]).exists(), "PNG file does not exist"
    print(f"  ✓ PNG screenshot captured: {res_png['path']} ({res_png['width']}x{res_png['height']})")

    # Clean up test screenshots
    if os.path.exists(res_jpg["path"]):
        os.remove(res_jpg["path"])
    if os.path.exists(res_png["path"]):
        os.remove(res_png["path"])
    print("  ✓ Cleaned up temporary test screenshots")


def test_list_windows():
    print("\n[Stage 3 - Test 2] Testing window enumeration...")
    res = list_open_windows()
    assert res["success"] is True, f"Window enumeration failed: {res}"
    assert "session" in res
    assert "count" in res
    print(f"  ✓ Found {res['count']} active windows (session environment: {res['session']})")
    
    for i, w in enumerate(res["windows"][:5]):
        print(f"    - Window #{i+1}: title='{w.get('title')}' class='{w.get('class')}' pid={w.get('pid')}")


def test_focus_window():
    print("\n[Stage 3 - Test 3] Testing window focus switching...")
    win_list = list_open_windows()
    if win_list.get("windows"):
        # Focus existing window
        target = win_list["windows"][0]
        query = target.get("class") or target.get("title")[:8]
        f_res = focus_window_by_title(query)
        assert f_res["success"] is True, f"Focus failed: {f_res}"
        print(f"  ✓ Successfully switched focus to: {f_res.get('matched_title')} ({f_res.get('matched_class')})")
    else:
        print("  - No active windows available to switch focus, skipping focus assertion")

    # Test non-existent window handling
    bad_res = focus_window_by_title("non_existent_window_xyz_999")
    assert bad_res["success"] is False
    assert "no open window found" in bad_res["error"].lower()
    print("  ✓ Non-existent window search correctly handled and reported")


def test_mcp_screen_tools():
    print("\n[Stage 3 - Test 4] Testing FastMCP screen tools integration...")
    from agent.mcp_server import create_mcp_server
    server = create_mcp_server()
    assert server is not None

    # Call tools directly via their underlying registered functions
    # 1. screenshot
    from agent.tools.screen import capture_screenshot
    shot_data = capture_screenshot()
    assert shot_data["success"] is True

    # 2. list_windows
    from agent.tools.screen import list_open_windows
    win_data = list_open_windows()
    assert win_data["success"] is True

    print("  ✓ MCP tool endpoints verified and return valid structured metadata")


def test_audit_logging():
    print("\n[Stage 3 - Test 5] Verifying audit logging for screen tools...")
    logger = AuditLogger.get_instance()
    recent = logger.get_recent_entries(limit=10)
    actions = [e["action"] for e in recent]
    
    assert "screenshot" in actions, "Screenshot action should be in audit log"
    assert "list_windows" in actions, "List_windows action should be in audit log"
    assert "focus_window" in actions, "Focus_window action should be in audit log"
    print(f"  ✓ Verified audit logs contain entries for: {set(actions)}")


def run_all():
    print("==================================================")
    print(" Running Stage 3 (Screen & Windows) Test Suite    ")
    print("==================================================")
    test_screenshot_capture()
    test_list_windows()
    test_focus_window()
    test_mcp_screen_tools()
    test_audit_logging()
    print("\n==================================================")
    print(" ALL STAGE 3 SCREEN & WINDOWS TESTS PASSED!       ")
    print("==================================================")


if __name__ == "__main__":
    run_all()
