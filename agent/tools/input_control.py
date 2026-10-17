"""GUI automation tool for remote mouse and keyboard control with mandatory approval.

Enforces:
1. Strict Human-in-the-Loop approval for ALL mouse and keyboard mutations.
2. Cross-platform execution (pynput, pyautogui, and xdotool fallbacks).
3. Structured JSONL audit logging for every attempted and executed GUI action.
"""

import os
import platform
import shutil
import subprocess
import time
from typing import Any, Dict, Optional

from agent.safety.approvals import ApprovalManager
from agent.safety.audit import AuditLogger
from agent.safety.policy import SecurityPolicy


def _enforce_approval(
    action: str,
    params: Dict[str, Any],
    approval_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Verify whether the requested GUI action has valid human approval.

    If in read-only mode, rejects the action immediately.
    If not approved, registers a new pending request and returns the pending response dict.
    If already approved, returns None to allow execution.
    """
    policy = SecurityPolicy.get_instance()
    logger = AuditLogger.get_instance()

    # Block completely in read-only mode
    if policy.mode == "read-only":
        err_msg = f"GUI action '{action}' is blocked in 'read-only' mode."
        logger.log(
            action=action,
            params=params,
            status="blocked",
            error=err_msg,
        )
        return {
            "success": False,
            "status": "blocked",
            "error": err_msg,
            "action": action,
            "params": params,
        }

    approval_mgr = ApprovalManager.get_instance()

    # Check if an approval token was provided and marked approved
    if approval_id and approval_mgr.check_status(approval_id) == "approved":
        return None


    # Action requires approval -> register new request
    req = approval_mgr.create_request(action=action, details=params)
    logger.log(
        action=action,
        params=params,
        status="pending_approval",
        error=f"GUI action '{action}' held for human approval (approval_id: {req.id})",
    )

    return {
        "success": False,
        "status": "pending_approval",
        "approval_id": req.id,
        "action": action,
        "params": params,
        "message": (
            f"GUI control action '{action}' requires explicit human confirmation before execution. "
            f"Approval ID: '{req.id}'. "
            f"Approve via approve_action(approval_id='{req.id}') or the Web Viewer UI."
        ),
    }


def mouse_click(
    x: int,
    y: int,
    button: str = "left",
    approval_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Click a mouse button at specified screen coordinates (requires human approval).

    Args:
        x: Horizontal pixel coordinate on the desktop.
        y: Vertical pixel coordinate on the desktop.
        button: Mouse button to click: 'left', 'right', or 'middle' (default: 'left').
        approval_id: Approval token if action was previously held for confirmation.

    Returns:
        Dict indicating success status, coordinates, and execution time.
    """
    params = {"x": x, "y": y, "button": button}
    pending = _enforce_approval("click", params, approval_id)
    if pending:
        return pending

    logger = AuditLogger.get_instance()
    start_time = time.time()
    clicked = False
    err_msg = None

    # Method 1: pynput
    try:
        from pynput.mouse import Button, Controller

        mouse = Controller()
        mouse.position = (x, y)
        time.sleep(0.05)
        btn_map = {"left": Button.left, "right": Button.right, "middle": Button.middle}
        target_btn = btn_map.get(button.lower(), Button.left)
        mouse.click(target_btn)
        clicked = True
    except Exception as e:
        err_msg = str(e)

    # Method 2: pyautogui fallback
    if not clicked:
        try:
            import pyautogui

            pyautogui.click(x=x, y=y, button=button.lower())
            clicked = True
        except Exception as e:
            err_msg = str(e)

    # Method 3: xdotool on Linux X11/XWayland
    if not clicked and shutil.which("xdotool"):
        try:
            btn_num = {"left": "1", "middle": "2", "right": "3"}.get(button.lower(), "1")
            res = subprocess.run(["xdotool", "mousemove", str(x), str(y), "click", btn_num], capture_output=True, timeout=2)
            if res.returncode == 0:
                clicked = True
        except Exception as e:
            err_msg = str(e)

    duration_ms = (time.time() - start_time) * 1000
    if clicked:
        logger.log(action="click", params=params, status="executed", duration_ms=duration_ms)
        return {"success": True, "action": "click", "x": x, "y": y, "button": button, "duration_ms": round(duration_ms, 2)}
    else:
        logger.log(action="click", params=params, status="failed", duration_ms=duration_ms, error=err_msg)
        return {"success": False, "error": f"Failed to execute mouse click: {err_msg}", "params": params}


def mouse_double_click(
    x: int,
    y: int,
    approval_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Double-click mouse left button at specified coordinates (requires human approval).

    Args:
        x: Horizontal pixel coordinate.
        y: Vertical pixel coordinate.
        approval_id: Approval token if action was previously held for confirmation.

    Returns:
        Dict with execution status.
    """
    params = {"x": x, "y": y}
    pending = _enforce_approval("double_click", params, approval_id)
    if pending:
        return pending

    logger = AuditLogger.get_instance()
    start_time = time.time()
    clicked = False
    err_msg = None

    # Method 1: pynput
    try:
        from pynput.mouse import Button, Controller

        mouse = Controller()
        mouse.position = (x, y)
        time.sleep(0.05)
        mouse.click(Button.left, 2)
        clicked = True
    except Exception as e:
        err_msg = str(e)

    # Method 2: pyautogui
    if not clicked:
        try:
            import pyautogui

            pyautogui.doubleClick(x=x, y=y)
            clicked = True
        except Exception as e:
            err_msg = str(e)

    # Method 3: xdotool
    if not clicked and shutil.which("xdotool"):
        try:
            res = subprocess.run(["xdotool", "mousemove", str(x), str(y), "click", "--repeat", "2", "1"], capture_output=True, timeout=2)
            if res.returncode == 0:
                clicked = True
        except Exception as e:
            err_msg = str(e)

    duration_ms = (time.time() - start_time) * 1000
    if clicked:
        logger.log(action="double_click", params=params, status="executed", duration_ms=duration_ms)
        return {"success": True, "action": "double_click", "x": x, "y": y, "duration_ms": round(duration_ms, 2)}
    else:
        logger.log(action="double_click", params=params, status="failed", duration_ms=duration_ms, error=err_msg)
        return {"success": False, "error": f"Failed to execute double click: {err_msg}", "params": params}


def keyboard_type(
    text: str,
    approval_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Type a string of text into the currently focused desktop window (requires human approval).

    Args:
        text: String of text characters to type.
        approval_id: Approval token if action was previously held for confirmation.

    Returns:
        Dict indicating number of characters typed and status.
    """
    params = {"text": text, "length": len(text)}
    pending = _enforce_approval("type_text", params, approval_id)
    if pending:
        return pending

    logger = AuditLogger.get_instance()
    start_time = time.time()
    typed = False
    err_msg = None

    # Method 1: pynput
    try:
        from pynput.keyboard import Controller

        kb = Controller()
        kb.type(text)
        typed = True
    except Exception as e:
        err_msg = str(e)

    # Method 2: pyautogui
    if not typed:
        try:
            import pyautogui

            pyautogui.write(text, interval=0.01)
            typed = True
        except Exception as e:
            err_msg = str(e)

    # Method 3: xdotool
    if not typed and shutil.which("xdotool"):
        try:
            res = subprocess.run(["xdotool", "type", "--delay", "10", text], capture_output=True, timeout=5)
            if res.returncode == 0:
                typed = True
        except Exception as e:
            err_msg = str(e)

    duration_ms = (time.time() - start_time) * 1000
    if typed:
        logger.log(action="type_text", params={"length": len(text)}, status="executed", duration_ms=duration_ms)
        return {"success": True, "action": "type_text", "characters_typed": len(text), "duration_ms": round(duration_ms, 2)}
    else:
        logger.log(action="type_text", params={"length": len(text)}, status="failed", duration_ms=duration_ms, error=err_msg)
        return {"success": False, "error": f"Failed to type text: {err_msg}"}


def keyboard_press(
    key: str,
    approval_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Press a special or standard keyboard key (e.g. 'enter', 'tab', 'escape', 'ctrl+c') (requires approval).

    Args:
        key: Key name or combination (e.g., 'Return', 'BackSpace', 'Escape', 'Tab', 'ctrl+v').
        approval_id: Approval token if action was previously held for confirmation.

    Returns:
        Dict indicating key pressed and status.
    """
    params = {"key": key}
    pending = _enforce_approval("press_key", params, approval_id)
    if pending:
        return pending

    logger = AuditLogger.get_instance()
    start_time = time.time()
    pressed = False
    err_msg = None

    # Normalize key name
    k_norm = key.strip()

    # Method 1: pyautogui
    try:
        import pyautogui

        if "+" in k_norm:
            parts = [p.strip().lower() for p in k_norm.split("+")]
            pyautogui.hotkey(*parts)
        else:
            pyautogui.press(k_norm.lower())
        pressed = True
    except Exception as e:
        err_msg = str(e)

    # Method 2: pynput fallback
    if not pressed:
        try:
            from pynput.keyboard import Controller, Key

            kb = Controller()
            special_keys = {
                "enter": Key.enter,
                "return": Key.enter,
                "tab": Key.tab,
                "space": Key.space,
                "backspace": Key.backspace,
                "escape": Key.esc,
                "esc": Key.esc,
                "up": Key.up,
                "down": Key.down,
                "left": Key.left,
                "right": Key.right,
            }
            k_lower = k_norm.lower()
            if k_lower in special_keys:
                kb.press(special_keys[k_lower])
                kb.release(special_keys[k_lower])
                pressed = True
            elif len(k_norm) == 1:
                kb.press(k_norm)
                kb.release(k_norm)
                pressed = True
        except Exception as e:
            err_msg = str(e)

    # Method 3: xdotool
    if not pressed and shutil.which("xdotool"):
        try:
            res = subprocess.run(["xdotool", "key", k_norm], capture_output=True, timeout=2)
            if res.returncode == 0:
                pressed = True
        except Exception as e:
            err_msg = str(e)

    duration_ms = (time.time() - start_time) * 1000
    if pressed:
        logger.log(action="press_key", params=params, status="executed", duration_ms=duration_ms)
        return {"success": True, "action": "press_key", "key": key, "duration_ms": round(duration_ms, 2)}
    else:
        logger.log(action="press_key", params=params, status="failed", duration_ms=duration_ms, error=err_msg)
        return {"success": False, "error": f"Failed to press key '{key}': {err_msg}"}


def mouse_scroll(
    amount: int,
    x: Optional[int] = None,
    y: Optional[int] = None,
    approval_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Scroll mouse wheel up (positive) or down (negative) (requires human approval).

    Args:
        amount: Number of scroll steps (e.g. 5 for up, -5 for down).
        x: Optional horizontal coordinate to position cursor before scrolling.
        y: Optional vertical coordinate to position cursor before scrolling.
        approval_id: Approval token if action was previously held for confirmation.

    Returns:
        Dict with scroll result.
    """
    params = {"amount": amount, "x": x, "y": y}
    pending = _enforce_approval("scroll", params, approval_id)
    if pending:
        return pending

    logger = AuditLogger.get_instance()
    start_time = time.time()
    scrolled = False
    err_msg = None

    # Method 1: pynput
    try:
        from pynput.mouse import Controller

        mouse = Controller()
        if x is not None and y is not None:
            mouse.position = (x, y)
        mouse.scroll(0, amount)
        scrolled = True
    except Exception as e:
        err_msg = str(e)

    # Method 2: pyautogui
    if not scrolled:
        try:
            import pyautogui

            if x is not None and y is not None:
                pyautogui.moveTo(x, y)
            pyautogui.scroll(amount * 10)
            scrolled = True
        except Exception as e:
            err_msg = str(e)

    # Method 3: xdotool
    if not scrolled and shutil.which("xdotool"):
        try:
            # 4 is scroll up, 5 is scroll down
            btn = "4" if amount > 0 else "5"
            clicks = abs(amount)
            args = ["xdotool"]
            if x is not None and y is not None:
                args += ["mousemove", str(x), str(y)]
            args += ["click", "--repeat", str(clicks), btn]
            res = subprocess.run(args, capture_output=True, timeout=2)
            if res.returncode == 0:
                scrolled = True
        except Exception as e:
            err_msg = str(e)

    duration_ms = (time.time() - start_time) * 1000
    if scrolled:
        logger.log(action="scroll", params=params, status="executed", duration_ms=duration_ms)
        return {"success": True, "action": "scroll", "amount": amount, "duration_ms": round(duration_ms, 2)}
    else:
        logger.log(action="scroll", params=params, status="failed", duration_ms=duration_ms, error=err_msg)
        return {"success": False, "error": f"Failed to scroll mouse: {err_msg}"}
