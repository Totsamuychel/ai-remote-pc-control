"""FastMCP Server implementation for AI Remote PC Control.

Exposes safe remote PC management tools conforming to Model Context Protocol (MCP):
- ping: Server health check and mode inspection
- run_command: Sandboxed terminal execution with audit logging
- read_file: Sandboxed file inspection
- write_file: Sandboxed file creation and modification
- list_dir: Directory inspection with file metadata
- list_processes: Inspection of running system processes
- kill_process: Process termination with protected PID safety
- pending_approvals: List operations pending user confirmation
- approve_action: Approve a pending high-risk operation
"""

import json
from typing import Any, Dict, Optional

try:
    # MCP SDK 2.x (FastMCP renamed to MCPServer)
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:
    try:
        # MCP SDK 1.x
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        try:
            # Standalone fastmcp package
            from fastmcp import FastMCP  # type: ignore
        except ImportError:
            FastMCP = None  # Handled in create_server()

from agent.safety.approvals import ApprovalManager
from agent.safety.audit import AuditLogger
from agent.safety.policy import SecurityPolicy
from agent.tools.files import list_directory, read_file_content, write_file_content
from agent.tools.processes import list_system_processes, terminate_process
from agent.tools.input_control import keyboard_press, keyboard_type, mouse_click, mouse_double_click, mouse_scroll
from agent.tools.screen import capture_screenshot, focus_window_by_title, list_open_windows
from agent.tools.terminal import execute_terminal_command


def create_mcp_server(name: str = "RemotePCControl", config_path: Optional[str] = None):
    """Instantiate and configure the FastMCP server with all registered tools."""
    if FastMCP is None:
        raise RuntimeError(
            "MCP library is not installed. Please run: pip install -r requirements.txt (installs 'mcp>=1.2.0')"
        )

    # Initialize policy and logger
    policy = SecurityPolicy.get_instance(config_path=config_path)
    logger = AuditLogger.get_instance()
    approval_mgr = ApprovalManager.get_instance()

    mcp = FastMCP(name)

    @mcp.tool()
    def ping() -> str:
        """Check if the remote PC control server is alive and return current security policy mode.

        Returns:
            JSON string with status 'pong', security mode, server version, and allowed paths.
        """
        data = {
            "status": "pong",
            "server": name,
            "security_mode": policy.mode,
            "allowed_directories": [str(d) for d in policy.allowed_directories],
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    @mcp.tool()
    def run_command(
        command: str,
        cwd: str = "",
        timeout: int = 30,
        approval_id: str = "",
    ) -> str:
        """Execute a shell command on the remote PC within the sandboxed environment.

        Safety Rules:
        - Destructive commands (rm -rf /, formatting, partition writes) are strictly blocked.
        - In 'safe-execute' mode, commands outside the safe whitelist will require human approval.
        - Execution path (cwd) must reside within allowed sandbox directories.
        - Full command execution and outputs are recorded in the JSONL audit log.

        Args:
            command: Shell command string to execute (e.g. 'ls -la', 'python script.py').
            cwd: Working directory to run command in. Defaults to current sandbox directory.
            timeout: Maximum allowed execution time in seconds (default: 30).
            approval_id: Approval ID token if command previously prompted for user approval.

        Returns:
            JSON string containing success flag, exit_code, stdout, stderr, and duration.
        """
        res = execute_terminal_command(
            command=command,
            cwd=cwd,
            timeout=timeout,
            approval_id=approval_id if approval_id else None,
        )
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def read_file(
        path: str,
        max_bytes: int = 2097152,
    ) -> str:
        """Read text contents of a file on the remote PC.

        Safety Rules:
        - Path must be located inside allowed directories (~, /tmp, project directory).
        - Path traversal attempts (e.g., ../../etc/shadow) are rejected.
        - Maximum read limit is enforced to prevent buffer overflow (default: 2 MB).

        Args:
            path: Absolute or relative path to the file.
            max_bytes: Maximum number of bytes to read (default: 2097152 / 2MB).

        Returns:
            JSON string with file content, size in bytes, and resolved path.
        """
        res = read_file_content(path=path, max_bytes=max_bytes)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def write_file(
        path: str,
        content: str,
        append: bool = False,
    ) -> str:
        """Create or modify a file on the remote PC.

        Safety Rules:
        - Blocked entirely in 'read-only' mode.
        - Target path must reside inside allowed sandbox directories.
        - Parent directories will be automatically created if they don't exist.
        - All modifications are logged to the audit log.

        Args:
            path: Target file path.
            content: Text content to write.
            append: If True, appends to the file instead of overwriting (default: False).

        Returns:
            JSON string with status, path, and number of bytes written.
        """
        res = write_file_content(path=path, content=content, append=append)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def list_dir(
        path: str = ".",
    ) -> str:
        """List files and subdirectories inside a given path on the remote PC.

        Safety Rules:
        - Inspected path must reside within allowed sandbox directories.
        - Traversal attempts outside the sandbox are rejected.

        Args:
            path: Target directory path to inspect (defaults to current directory).

        Returns:
            JSON string with count and list of entries (name, type, size_bytes, modified).
        """
        res = list_directory(path=path)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def list_processes(
        limit: int = 50,
        sort_by: str = "cpu",
    ) -> str:
        """List currently running processes on the remote PC with resource statistics.

        Args:
            limit: Maximum number of processes to return (default: 50).
            sort_by: Metric to sort by: 'cpu', 'memory', or 'pid' (default: 'cpu').

        Returns:
            JSON string with list of processes (pid, name, user, cpu%, memory%, status).
        """
        res = list_system_processes(limit=limit, sort_by=sort_by)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def kill_process(
        pid: int,
        force: bool = False,
        approval_id: str = "",
    ) -> str:
        """Terminate a running process by PID on the remote PC.

        Safety Rules:
        - Cannot terminate system init processes (PID 0, PID 1).
        - Cannot terminate the remote PC agent itself.
        - In 'safe-execute' mode, process termination requires human confirmation.

        Args:
            pid: Process ID to terminate.
            force: If True, sends SIGKILL (kill -9); otherwise sends SIGTERM (default: False).
            approval_id: Approval ID if action was previously held for confirmation.

        Returns:
            JSON string with operation result or pending approval details.
        """
        res = terminate_process(
            pid=pid,
            force=force,
            approval_id=approval_id if approval_id else None,
        )
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def pending_approvals() -> str:
        """List all current actions awaiting human approval.

        Returns:
            JSON string with active approval requests and their IDs.
        """
        items = approval_mgr.list_pending()
        return json.dumps({"count": len(items), "pending": items}, indent=2, ensure_ascii=False)

    @mcp.tool()
    def approve_action(approval_id: str) -> str:
        """Grant approval for a previously held high-risk operation.

        Args:
            approval_id: The 8-character approval identifier returned in a pending request.

        Returns:
            JSON string with confirmation status.
        """
        success = approval_mgr.approve(approval_id)
        return json.dumps(
            {
                "success": success,
                "approval_id": approval_id,
                "message": (
                    f"Approval '{approval_id}' granted. You can now re-run the tool with approval_id='{approval_id}'."
                    if success
                    else f"Approval '{approval_id}' not found or already expired."
                ),
            },
            indent=2,
            ensure_ascii=False,
        )

    @mcp.tool()
    def screenshot(
        output_path: str = "",
        quality: int = 80,
        format: str = "jpeg",
    ) -> str:
        """Capture a screenshot of the remote desktop screen and save to a temporary file.

        Args:
            output_path: Optional custom destination file path (defaults to /tmp/remote_pc_screenshots/...).
            quality: Compression quality for JPEG format (1-100, default: 80).
            format: Image format: 'jpeg' or 'png' (default: 'jpeg').

        Returns:
            JSON string with success status, image dimensions (width, height), size in bytes,
            temporary file path, and descriptive summary.
        """
        res = capture_screenshot(output_path=output_path, quality=quality, format=format)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def list_windows() -> str:
        """List currently open and active application windows on the remote desktop.

        Inspects active desktop windows across Hyprland, Sway, X11, or Windows environments.

        Returns:
            JSON string with total window count, active session environment, and list of
            windows (id, title, class, pid, workspace, active status).
        """
        res = list_open_windows()
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def focus_window(
        title: str,
    ) -> str:
        """Switch active desktop focus to an open window matching the given title or class name.

        Args:
            title: Query substring matching window title, application class name, or window ID.

        Returns:
            JSON string indicating success status, matched window title/class, and status message.
        """
        res = focus_window_by_title(query=title)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def view_terminal(
        cols: int = 80,
    ) -> str:
        """Capture desktop screen and render it directly as formatted text for terminal viewing.

        Uses 24-bit TrueColor ANSI escape sequences with Unicode half-block characters (▀).
        Allows AI assistants and terminal users to inspect the graphical desktop layout directly
        within their CLI session.

        Args:
            cols: Horizontal resolution in terminal columns (default: 80).

        Returns:
            ANSI formatted string rendering of the current desktop screen.
        """
        from streaming.terminal_viewer import render_ansi_halfblock

        tmp_path = "/tmp/remote_pc_mcp_terminal_view.jpg"
        shot = capture_screenshot(output_path=tmp_path, quality=75)
        if not shot.get("success"):
            return f"[Error] Screen capture failed: {shot.get('error')}"

        try:
            ansi_text = render_ansi_halfblock(tmp_path, max_cols=cols)
            header = f"\n=== Remote PC Desktop Screen ({shot.get('width')}x{shot.get('height')}) ===\n"
            return header + ansi_text + "\n"
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    @mcp.tool()
    def click(
        x: int,
        y: int,
        button: str = "left",
        approval_id: str = "",
    ) -> str:
        """Click mouse button at desktop coordinates (requires human approval).

        Safety Rules:
        - All GUI input actions strictly enforce require_approval=true.
        - If no valid approval_id is provided, returns pending_approval status with an approval token.
        - The user must grant consent before the click can be dispatched.

        Args:
            x: Target horizontal pixel coordinate on the desktop.
            y: Target vertical pixel coordinate on the desktop.
            button: Mouse button to click: 'left', 'right', or 'middle' (default: 'left').
            approval_id: 8-character approval token once approved by user.

        Returns:
            JSON string with status, coordinates, and execution result or approval prompt.
        """
        res = mouse_click(x=x, y=y, button=button, approval_id=approval_id if approval_id else None)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def double_click(
        x: int,
        y: int,
        approval_id: str = "",
    ) -> str:
        """Double-click mouse left button at desktop coordinates (requires human approval).

        Args:
            x: Target horizontal coordinate.
            y: Target vertical coordinate.
            approval_id: 8-character approval token once approved by user.

        Returns:
            JSON string with status and execution result.
        """
        res = mouse_double_click(x=x, y=y, approval_id=approval_id if approval_id else None)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def type_text(
        text: str,
        approval_id: str = "",
    ) -> str:
        """Type text into the currently active desktop window (requires human approval).

        Args:
            text: String text sequence to type.
            approval_id: 8-character approval token once approved by user.

        Returns:
            JSON string with number of characters typed and status.
        """
        res = keyboard_type(text=text, approval_id=approval_id if approval_id else None)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def press_key(
        key: str,
        approval_id: str = "",
    ) -> str:
        """Press a special or standard keyboard key (requires human approval).

        Args:
            key: Key name or hotkey combination (e.g. 'Return', 'Tab', 'Escape', 'ctrl+c').
            approval_id: 8-character approval token once approved by user.

        Returns:
            JSON string with key pressed and status.
        """
        res = keyboard_press(key=key, approval_id=approval_id if approval_id else None)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def scroll(
        amount: int,
        x: int = 0,
        y: int = 0,
        approval_id: str = "",
    ) -> str:
        """Scroll mouse wheel vertically (requires human approval).

        Args:
            amount: Number of scroll notches (positive = scroll up, negative = scroll down).
            x: Optional horizontal position for cursor before scrolling.
            y: Optional vertical position for cursor before scrolling.
            approval_id: 8-character approval token once approved by user.

        Returns:
            JSON string with scroll result.
        """
        res = mouse_scroll(
            amount=amount,
            x=x if (x > 0 or y > 0) else None,
            y=y if (x > 0 or y > 0) else None,
            approval_id=approval_id if approval_id else None,
        )
        return json.dumps(res, indent=2, ensure_ascii=False)

    return mcp
