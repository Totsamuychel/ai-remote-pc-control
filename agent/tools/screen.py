"""Screen capture and desktop window management tool.

Supports:
1. Multi-monitor screenshot capture (Wayland via grim, X11/Windows via mss & Pillow).
2. Active desktop window enumeration (Hyprland, Sway, X11 wmctrl, Windows API).
3. Window focus switching across Linux compositors and Windows.
4. Graceful error handling for headless and non-graphical environments.
"""

import json
import os
import platform
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.safety.audit import AuditLogger


def _has_graphical_session() -> bool:
    """Check if the current environment has an active graphical display session."""
    if platform.system() == "Windows":
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def capture_screenshot(
    output_path: str = "",
    quality: int = 80,
    format: str = "jpeg",
) -> Dict[str, Any]:
    """Capture full desktop screenshot and save to a temporary location.

    Args:
        output_path: Optional custom destination file path.
        quality: JPEG compression quality (1-100, default: 80).
        format: Image format: 'jpeg' or 'png' (default: 'jpeg').

    Returns:
        Dict containing success status, image dimensions, file path, size, and description.
    """
    logger = AuditLogger.get_instance()
    start_time = time.time()

    if not _has_graphical_session():
        duration_ms = (time.time() - start_time) * 1000
        err = "No active graphical display session detected (DISPLAY and WAYLAND_DISPLAY are unset)."
        logger.log(action="screenshot", status="failed", duration_ms=duration_ms, error=err)
        return {"success": False, "error": err}

    # Prepare default output path in /tmp or temp directory
    ext = "jpg" if format.lower() in ("jpg", "jpeg") else "png"
    if not output_path:
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_dir = Path("/tmp/remote_pc_screenshots")
        temp_dir.mkdir(parents=True, exist_ok=True)
        dest_file = temp_dir / f"screenshot_{timestamp_str}.{ext}"
    else:
        dest_file = Path(output_path).expanduser().resolve()
        dest_file.parent.mkdir(parents=True, exist_ok=True)

    captured = False
    width, height = 0, 0

    # Strategy 1: Wayland native capture via 'grim'
    if os.environ.get("WAYLAND_DISPLAY") and shutil.which("grim"):
        try:
            raw_png = dest_file.with_suffix(".raw.png")
            proc = subprocess.run(["grim", str(raw_png)], capture_output=True, timeout=5)
            if proc.returncode == 0 and raw_png.exists():
                try:
                    from PIL import Image

                    with Image.open(raw_png) as img:
                        width, height = img.size
                        if format.lower() in ("jpg", "jpeg"):
                            rgb_img = img.convert("RGB")
                            rgb_img.save(dest_file, format="JPEG", quality=quality)
                            raw_png.unlink(missing_ok=True)
                        else:
                            raw_png.replace(dest_file)
                    captured = True
                except ImportError:
                    # If PIL is somehow unavailable, keep raw png
                    raw_png.replace(dest_file)
                    captured = True
        except Exception:
            captured = False

    # Strategy 2: Cross-platform capture via 'mss' and 'Pillow'
    if not captured:
        try:
            import mss
            from PIL import Image

            # Use mss.MSS (or mss.mss fallback)
            sct_cls = getattr(mss, "MSS", getattr(mss, "mss", None))
            with sct_cls() as sct:
                # Monitor 0 is full virtual screen (all monitors combined)
                mon = sct.monitors[0]
                shot = sct.grab(mon)
                width, height = shot.width, shot.height

                img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
                save_fmt = "JPEG" if format.lower() in ("jpg", "jpeg") else "PNG"
                img.save(dest_file, format=save_fmt, quality=quality if save_fmt == "JPEG" else None)
                captured = True
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            err = f"Failed to capture screen using mss/grim: {e}"
            logger.log(action="screenshot", status="failed", duration_ms=duration_ms, error=err)
            return {"success": False, "error": err}

    if not dest_file.exists():
        duration_ms = (time.time() - start_time) * 1000
        err = "Screenshot file was not generated."
        logger.log(action="screenshot", status="failed", duration_ms=duration_ms, error=err)
        return {"success": False, "error": err}

    size_bytes = dest_file.stat().st_size
    duration_ms = (time.time() - start_time) * 1000
    description = f"Desktop screenshot captured ({width}x{height}, {round(size_bytes / 1024, 1)} KB)"

    logger.log(
        action="screenshot",
        params={"path": str(dest_file), "quality": quality, "format": format},
        status="executed",
        duration_ms=duration_ms,
        output_summary=description,
    )

    return {
        "success": True,
        "path": str(dest_file),
        "width": width,
        "height": height,
        "size_bytes": size_bytes,
        "format": ext,
        "duration_ms": round(duration_ms, 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "description": description,
    }


def list_open_windows() -> Dict[str, Any]:
    """Enumerate currently open application windows on the desktop.

    Returns:
        Dict with list of windows (id, title, class_name, pid, workspace, active).
    """
    logger = AuditLogger.get_instance()
    start_time = time.time()

    if not _has_graphical_session():
        duration_ms = (time.time() - start_time) * 1000
        err = "No graphical display session available to list windows."
        logger.log(action="list_windows", status="failed", duration_ms=duration_ms, error=err)
        return {"success": False, "error": err, "windows": []}

    windows: List[Dict[str, Any]] = []
    session_info = "unknown"

    # 1. Linux Hyprland compositor
    if shutil.which("hyprctl"):
        try:
            res = subprocess.run(["hyprctl", "clients", "-j"], capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                session_info = "wayland (hyprland)"
                data = json.loads(res.stdout)
                for client in data:
                    title = client.get("title", "")
                    class_name = client.get("class", "")
                    # Skip empty / background windows
                    if not title and not class_name:
                        continue
                    windows.append({
                        "id": client.get("address", ""),
                        "title": title,
                        "class": class_name,
                        "pid": client.get("pid"),
                        "workspace": client.get("workspace", {}).get("name", ""),
                        "size": client.get("size", []),
                        "position": client.get("at", []),
                        "active": client.get("focusHistoryID") == 0,
                    })
        except Exception:
            pass

    # 2. Linux Sway compositor
    if not windows and shutil.which("swaymsg"):
        try:
            res = subprocess.run(["swaymsg", "-t", "get_tree"], capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                session_info = "wayland (sway)"
                tree = json.loads(res.stdout)

                def extract_sway_windows(node):
                    if node.get("type") in ("con", "floating_con") and node.get("name"):
                        windows.append({
                            "id": str(node.get("id", "")),
                            "title": node.get("name", ""),
                            "class": node.get("app_id") or node.get("window_properties", {}).get("class", ""),
                            "pid": node.get("pid"),
                            "focused": node.get("focused", False),
                        })
                    for child in node.get("nodes", []) + node.get("floating_nodes", []):
                        extract_sway_windows(child)

                extract_sway_windows(tree)
        except Exception:
            pass

    # 3. Linux X11 / XWayland via wmctrl
    if not windows and shutil.which("wmctrl"):
        try:
            res = subprocess.run(["wmctrl", "-lx"], capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                session_info = "x11 (wmctrl)"
                lines = res.stdout.strip().split("\n")
                for line in lines:
                    parts = line.split(None, 4)
                    if len(parts) >= 5:
                        win_id, ws, client_class, hostname, title = parts
                        windows.append({
                            "id": win_id,
                            "title": title.strip(),
                            "class": client_class.strip(),
                            "workspace": ws,
                            "active": False,
                        })
        except Exception:
            pass

    # 4. Windows OS via ctypes
    if not windows and platform.system() == "Windows":
        try:
            import ctypes
            from ctypes import wintypes

            session_info = "windows (user32)"
            user32 = ctypes.windll.user32

            def enum_windows_proc(hwnd, lParam):
                if user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buff, length + 1)
                        title = buff.value
                        # Get PID
                        pid = wintypes.DWORD()
                        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                        windows.append({
                            "id": str(hwnd),
                            "title": title,
                            "class": "",
                            "pid": pid.value,
                            "active": (hwnd == user32.GetForegroundWindow()),
                        })
                return True

            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
            user32.EnumWindows(WNDENUMPROC(enum_windows_proc), 0)
        except Exception:
            pass

    duration_ms = (time.time() - start_time) * 1000
    logger.log(
        action="list_windows",
        status="executed",
        duration_ms=duration_ms,
        output_summary=f"Found {len(windows)} active windows ({session_info})",
    )

    return {
        "success": True,
        "count": len(windows),
        "session": session_info,
        "windows": windows,
    }


def focus_window_by_title(
    query: str,
) -> Dict[str, Any]:
    """Switch active desktop focus to an open window matching the title, class, or address query.

    Args:
        query: Substring or identifier matching window title, application class name, or window address/ID.

    Returns:
        Dict indicating success status, matched window info, and message.
    """
    logger = AuditLogger.get_instance()
    start_time = time.time()

    if not _has_graphical_session():
        duration_ms = (time.time() - start_time) * 1000
        err = "No graphical display session available to switch window focus."
        logger.log(action="focus_window", params={"query": query}, status="failed", duration_ms=duration_ms, error=err)
        return {"success": False, "error": err}

    q = query.strip().lower()
    if not q:
        return {"success": False, "error": "Query parameter cannot be empty."}

    # Step 1: Enumerate windows to find best match
    win_list_res = list_open_windows()
    if not win_list_res.get("success") or not win_list_res.get("windows"):
        return {"success": False, "error": f"No open windows found to match query '{query}'."}

    matched_win = None
    for w in win_list_res["windows"]:
        title_lower = w.get("title", "").lower()
        class_lower = w.get("class", "").lower()
        id_lower = str(w.get("id", "")).lower()
        if q in title_lower or q in class_lower or q == id_lower:
            matched_win = w
            break

    if not matched_win:
        duration_ms = (time.time() - start_time) * 1000
        err = f"No open window found matching '{query}'."
        logger.log(action="focus_window", params={"query": query}, status="failed", duration_ms=duration_ms, error=err)
        return {"success": False, "error": err}

    matched_id = str(matched_win.get("id", ""))
    matched_title = matched_win.get("title", "")
    matched_class = matched_win.get("class", "")
    session_type = win_list_res.get("session", "")
    focus_success = False

    # Step 2: Focus the matched window using the appropriate platform method
    # 2a. Hyprland via Lua dispatch
    if "hyprland" in session_type and shutil.which("hyprctl"):
        clean_addr = matched_id.lower().strip()
        script = (
            f'(function() '
            f'for _, w in ipairs(hl.get_windows()) do '
            f'  if string.lower(tostring(w.address or "")) == "{clean_addr}" then '
            f'    return hl.dsp.focus({{ window = w }}) '
            f'  end '
            f'end '
            f'error("NOT_FOUND") '
            f'end)()'
        )
        try:
            res = subprocess.run(["hyprctl", "dispatch", script], capture_output=True, text=True, timeout=3)
            if res.returncode == 0 and "ok" in res.stdout:
                focus_success = True
        except Exception:
            pass

    # 2b. Sway
    elif "sway" in session_type and shutil.which("swaymsg"):
        try:
            cmd = ["swaymsg", f'[con_id="{matched_id}"] focus']
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                focus_success = True
        except Exception:
            pass

    # 2c. X11 via wmctrl
    elif "x11" in session_type and shutil.which("wmctrl"):
        try:
            # Try focusing by window ID directly
            res = subprocess.run(["wmctrl", "-i", "-a", matched_id], capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                focus_success = True
            else:
                # Fallback to focusing by title
                res = subprocess.run(["wmctrl", "-a", matched_title], capture_output=True, text=True, timeout=3)
                if res.returncode == 0:
                    focus_success = True
        except Exception:
            pass

    # 2d. Windows via ctypes
    elif platform.system() == "Windows":
        try:
            import ctypes
            hwnd = int(matched_id)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            focus_success = True
        except Exception:
            pass

    # Fallback to wmctrl if available regardless of detected session
    if not focus_success and shutil.which("wmctrl"):
        try:
            res = subprocess.run(["wmctrl", "-a", matched_title], capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                focus_success = True
        except Exception:
            pass

    duration_ms = (time.time() - start_time) * 1000
    if focus_success:
        logger.log(
            action="focus_window",
            params={"query": query, "matched_id": matched_id, "matched_title": matched_title},
            status="executed",
            duration_ms=duration_ms,
            output_summary=f"Focused window '{matched_title}' ({matched_class})",
        )
        return {
            "success": True,
            "matched_title": matched_title,
            "matched_class": matched_class,
            "id": matched_id,
            "message": f"Successfully focused window '{matched_title}' ({matched_class}).",
        }
    else:
        err = f"Failed to switch focus to window '{matched_title}' ({matched_class})."
        logger.log(action="focus_window", params={"query": query}, status="failed", duration_ms=duration_ms, error=err)
        return {"success": False, "error": err, "matched_title": matched_title}
