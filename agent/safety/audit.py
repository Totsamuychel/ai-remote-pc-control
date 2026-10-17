"""Audit logging system for AI Remote PC Control.

Records all actions, attempted operations, policy evaluations, and command executions
into structured JSONL files for compliance, debugging, and security auditing.
"""

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class AuditLogger:
    """Thread-safe JSONL audit logger."""

    _instance: Optional["AuditLogger"] = None
    _lock = threading.Lock()

    def __init__(self, log_path: str = "logs/audit.jsonl", enabled: bool = True):
        self.enabled = enabled
        self.log_file = Path(log_path).resolve()
        self._file_lock = threading.Lock()

        if self.enabled:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_instance(cls, log_path: str = "logs/audit.jsonl", enabled: bool = True) -> "AuditLogger":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(log_path=log_path, enabled=enabled)
            return cls._instance

    def log(
        self,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        status: str = "executed",  # allowed | blocked | executed | failed | pending_approval
        duration_ms: float = 0.0,
        exit_code: Optional[int] = None,
        output_summary: Optional[str] = None,
        error: Optional[str] = None,
        client: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record an entry in the audit log.

        Args:
            action: Name of the tool or internal operation (e.g., 'run_command').
            params: Dictionary of parameters passed to the action.
            status: Status of the action ('allowed', 'blocked', 'executed', 'failed', 'pending_approval').
            duration_ms: Duration of execution in milliseconds.
            exit_code: Process exit code if applicable.
            output_summary: Short summary or preview of execution output.
            error: Error message if operation failed or was blocked.
            client: Identifier for the client agent (e.g., Gemini CLI, Claude Code).

        Returns:
            The structured log record dictionary.
        """
        if not self.enabled:
            return {}

        # Sanitize parameters if long content is present
        sanitized_params = {}
        if params:
            for k, v in params.items():
                if isinstance(v, str) and len(v) > 200:
                    sanitized_params[k] = v[:200] + f"... [truncated, {len(v)} chars total]"
                else:
                    sanitized_params[k] = v

        # Truncate output summary if too long
        trimmed_summary = None
        if output_summary:
            trimmed_summary = (
                output_summary[:300] + f"... [truncated, {len(output_summary)} chars total]"
                if len(output_summary) > 300
                else output_summary
            )

        record: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "status": status,
            "params": sanitized_params,
            "duration_ms": round(duration_ms, 2),
            "exit_code": exit_code,
            "output_summary": trimmed_summary,
            "error": error,
            "client": client or "unknown",
        }

        try:
            line = json.dumps(record, ensure_ascii=False)
            with self._file_lock:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
        except Exception as e:
            # Audit logging failure should not crash the host, but log to stderr
            print(f"[AuditLogger Error] Failed to write log: {e}")

        return record

    def get_recent_entries(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Read recent audit records."""
        if not self.log_file.exists():
            return []

        entries = []
        try:
            with self._file_lock:
                with open(self.log_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    for line in reversed(lines[-limit:]):
                        line = line.strip()
                        if line:
                            entries.append(json.loads(line))
        except Exception as e:
            print(f"[AuditLogger Error] Failed to read logs: {e}")

        return entries
