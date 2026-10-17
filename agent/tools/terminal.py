"""Terminal execution tool with safety policy enforcement and audit logging."""

import os
import subprocess
import time
from typing import Any, Dict, Optional

from agent.safety.approvals import ApprovalManager
from agent.safety.audit import AuditLogger
from agent.safety.policy import SecurityPolicy, SecurityViolation


def execute_terminal_command(
    command: str,
    cwd: str = "",
    timeout: int = 30,
    approval_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute a shell command with strict security checks and audit logging.

    Args:
        command: The shell command line string to run.
        cwd: Working directory for command execution (must be within sandbox).
        timeout: Maximum execution time in seconds.
        approval_id: Optional approval token if command previously requested approval.

    Returns:
        Dict containing success status, exit_code, stdout, stderr, and execution time.
    """
    policy = SecurityPolicy.get_instance()
    logger = AuditLogger.get_instance()
    approval_mgr = ApprovalManager.get_instance()
    start_time = time.time()

    # 1. Resolve and validate working directory
    resolved_cwd = None
    if cwd:
        try:
            resolved_cwd = str(policy.validate_path(cwd, write=False))
        except SecurityViolation as sv:
            duration_ms = (time.time() - start_time) * 1000
            logger.log(
                action="run_command",
                params={"command": command, "cwd": cwd, "timeout": timeout},
                status="blocked",
                duration_ms=duration_ms,
                error=str(sv),
            )
            return {
                "success": False,
                "error": f"Working directory rejected by security policy: {sv}",
                "exit_code": -1,
                "stdout": "",
                "stderr": str(sv),
            }

    # 2. Validate command against security policy
    try:
        is_safe, warning = policy.validate_command(command)
    except SecurityViolation as sv:
        duration_ms = (time.time() - start_time) * 1000
        logger.log(
            action="run_command",
            params={"command": command, "cwd": cwd, "timeout": timeout},
            status="blocked",
            duration_ms=duration_ms,
            error=str(sv),
        )
        return {
            "success": False,
            "error": f"Command blocked by security policy: {sv}",
            "exit_code": -1,
            "stdout": "",
            "stderr": str(sv),
        }

    # 3. Handle unlisted commands in safe-execute mode requiring approval
    if not is_safe and policy.mode == "safe-execute":
        # Check if an approval ID was already granted
        if approval_id and approval_mgr.check_status(approval_id) == "approved":
            pass  # Approved, proceed to execution
        else:
            req = approval_mgr.create_request(
                action="run_command",
                details={"command": command, "cwd": cwd, "warning": warning},
            )
            duration_ms = (time.time() - start_time) * 1000
            logger.log(
                action="run_command",
                params={"command": command, "cwd": cwd, "approval_id": req.id},
                status="pending_approval",
                duration_ms=duration_ms,
                error=warning,
            )
            return {
                "success": False,
                "status": "pending_approval",
                "approval_id": req.id,
                "warning": warning,
                "message": (
                    f"Command requires human confirmation before execution: {warning}. "
                    f"Ask the user or use approve_action(approval_id='{req.id}') after getting permission."
                ),
                "exit_code": -1,
                "stdout": "",
                "stderr": "",
            }

    # 4. Execute command
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=resolved_cwd,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
        )

        duration_ms = (time.time() - start_time) * 1000

        result = {
            "success": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "duration_ms": round(duration_ms, 2),
            "cwd": resolved_cwd or os.getcwd(),
        }

        logger.log(
            action="run_command",
            params={"command": command, "cwd": cwd, "timeout": timeout},
            status="executed" if proc.returncode == 0 else "failed",
            duration_ms=duration_ms,
            exit_code=proc.returncode,
            output_summary=proc.stdout if proc.returncode == 0 else proc.stderr,
        )
        return result

    except subprocess.TimeoutExpired:
        duration_ms = (time.time() - start_time) * 1000
        err_msg = f"Command timed out after {timeout} seconds."
        logger.log(
            action="run_command",
            params={"command": command, "cwd": cwd, "timeout": timeout},
            status="failed",
            duration_ms=duration_ms,
            exit_code=-2,
            error=err_msg,
        )
        return {
            "success": False,
            "error": err_msg,
            "exit_code": -2,
            "stdout": "",
            "stderr": err_msg,
            "duration_ms": round(duration_ms, 2),
        }
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        err_msg = f"Unexpected execution error: {e}"
        logger.log(
            action="run_command",
            params={"command": command, "cwd": cwd, "timeout": timeout},
            status="failed",
            duration_ms=duration_ms,
            exit_code=-3,
            error=err_msg,
        )
        return {
            "success": False,
            "error": err_msg,
            "exit_code": -3,
            "stdout": "",
            "stderr": err_msg,
            "duration_ms": round(duration_ms, 2),
        }
