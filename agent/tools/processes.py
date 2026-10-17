"""Process inspection and management tool with safety controls and audit logging."""

import os
import signal
import subprocess
import time
from typing import Any, Dict, List, Optional

from agent.safety.approvals import ApprovalManager
from agent.safety.audit import AuditLogger
from agent.safety.policy import SecurityPolicy


def list_system_processes(
    limit: int = 50,
    sort_by: str = "cpu",  # cpu | memory | pid
) -> Dict[str, Any]:
    """Inspect currently running processes on the system.

    Args:
        limit: Maximum number of processes to return (default: 50).
        sort_by: Metric to sort processes by: 'cpu', 'memory', or 'pid'.

    Returns:
        Dict with status, count, and list of process information objects.
    """
    logger = AuditLogger.get_instance()
    start_time = time.time()

    processes: List[Dict[str, Any]] = []

    # Attempt to use psutil if available
    try:
        import psutil

        for proc in psutil.process_iter(["pid", "name", "username", "cpu_percent", "memory_percent", "status"]):
            try:
                info = proc.info
                processes.append({
                    "pid": info["pid"],
                    "name": info["name"] or "unknown",
                    "username": info["username"] or "unknown",
                    "cpu_percent": round(info["cpu_percent"] or 0.0, 1),
                    "memory_percent": round(info["memory_percent"] or 0.0, 1),
                    "status": info["status"] or "unknown",
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    except ImportError:
        # Fallback to standard Unix 'ps' command
        try:
            cmd = ["ps", "-eo", "pid,user,%cpu,%mem,comm", "--sort=-%cpu"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                lines = res.stdout.strip().split("\n")[1:]  # skip header
                for line in lines:
                    parts = line.split(None, 4)
                    if len(parts) >= 5:
                        try:
                            processes.append({
                                "pid": int(parts[0]),
                                "username": parts[1],
                                "cpu_percent": float(parts[2]),
                                "memory_percent": float(parts[3]),
                                "name": parts[4],
                                "status": "running",
                            })
                        except ValueError:
                            continue
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            err = f"Failed to inspect processes: {e}"
            logger.log(action="list_processes", status="failed", duration_ms=duration_ms, error=err)
            return {"success": False, "error": err, "processes": []}

    # Sort
    if sort_by == "memory":
        processes.sort(key=lambda p: p.get("memory_percent", 0.0), reverse=True)
    elif sort_by == "pid":
        processes.sort(key=lambda p: p.get("pid", 0))
    else:  # cpu
        processes.sort(key=lambda p: p.get("cpu_percent", 0.0), reverse=True)

    result_procs = processes[:limit]
    duration_ms = (time.time() - start_time) * 1000
    logger.log(
        action="list_processes",
        params={"limit": limit, "sort_by": sort_by},
        status="executed",
        duration_ms=duration_ms,
        output_summary=f"Retrieved {len(result_procs)} processes",
    )

    return {
        "success": True,
        "count": len(result_procs),
        "total_running": len(processes),
        "processes": result_procs,
    }


def terminate_process(
    pid: int,
    force: bool = False,
    approval_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Terminate a running process by PID with safety checks.

    Args:
        pid: Process ID to terminate.
        force: If True, send SIGKILL (9) instead of SIGTERM (15).
        approval_id: Optional approval token if termination required prior consent.

    Returns:
        Dict indicating success status, PID, and signal sent.
    """
    policy = SecurityPolicy.get_instance()
    logger = AuditLogger.get_instance()
    approval_mgr = ApprovalManager.get_instance()
    start_time = time.time()

    # 1. Check safety rule
    if not policy.is_kill_allowed(pid):
        duration_ms = (time.time() - start_time) * 1000
        err = f"Termination of protected process PID {pid} is forbidden."
        logger.log(
            action="kill_process",
            params={"pid": pid, "force": force},
            status="blocked",
            duration_ms=duration_ms,
            error=err,
        )
        return {"success": False, "error": err, "pid": pid}

    # 2. Block all process termination in read-only mode
    if policy.mode == "read-only":
        duration_ms = (time.time() - start_time) * 1000
        err = "Process termination is blocked in 'read-only' mode."
        logger.log(
            action="kill_process",
            params={"pid": pid, "force": force},
            status="blocked",
            duration_ms=duration_ms,
            error=err,
        )
        return {"success": False, "error": err, "pid": pid}

    # 3. Check approval requirement in safe-execute mode
    if policy.mode == "safe-execute":

        if approval_id and approval_mgr.check_status(approval_id) == "approved":
            pass  # Approved
        else:
            req = approval_mgr.create_request(
                action="kill_process",
                details={"pid": pid, "force": force},
            )
            duration_ms = (time.time() - start_time) * 1000
            msg = f"Terminating process PID {pid} requires user confirmation."
            logger.log(
                action="kill_process",
                params={"pid": pid, "force": force, "approval_id": req.id},
                status="pending_approval",
                duration_ms=duration_ms,
                error=msg,
            )
            return {
                "success": False,
                "status": "pending_approval",
                "approval_id": req.id,
                "message": f"{msg} Confirm with approve_action(approval_id='{req.id}').",
                "pid": pid,
            }

    # 3. Send signal
    sig = signal.SIGKILL if force else signal.SIGTERM
    try:
        os.kill(pid, sig)
        duration_ms = (time.time() - start_time) * 1000
        sig_name = "SIGKILL" if force else "SIGTERM"
        logger.log(
            action="kill_process",
            params={"pid": pid, "force": force},
            status="executed",
            duration_ms=duration_ms,
            output_summary=f"Sent {sig_name} to PID {pid}",
        )
        return {
            "success": True,
            "pid": pid,
            "signal": sig_name,
            "message": f"Successfully sent {sig_name} to PID {pid}.",
        }
    except ProcessLookupError:
        duration_ms = (time.time() - start_time) * 1000
        err = f"No process found with PID {pid}."
        logger.log(action="kill_process", params={"pid": pid}, status="failed", duration_ms=duration_ms, error=err)
        return {"success": False, "error": err, "pid": pid}
    except PermissionError:
        duration_ms = (time.time() - start_time) * 1000
        err = f"Permission denied to terminate PID {pid}."
        logger.log(action="kill_process", params={"pid": pid}, status="failed", duration_ms=duration_ms, error=err)
        return {"success": False, "error": err, "pid": pid}
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        err = f"Error terminating PID {pid}: {e}"
        logger.log(action="kill_process", params={"pid": pid}, status="failed", duration_ms=duration_ms, error=err)
        return {"success": False, "error": err, "pid": pid}
