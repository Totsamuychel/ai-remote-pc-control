"""File operations tool with sandboxing, path validation, and audit logging."""

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.safety.audit import AuditLogger
from agent.safety.policy import SecurityPolicy, SecurityViolation


def read_file_content(
    path: str,
    max_bytes: int = 2097152,  # 2 MB default
) -> Dict[str, Any]:
    """Read contents of a file within the sandboxed directories.

    Args:
        path: Path to the target file.
        max_bytes: Maximum number of bytes to read to prevent memory overload.

    Returns:
        Dict with status, file contents or error message, and metadata.
    """
    policy = SecurityPolicy.get_instance()
    logger = AuditLogger.get_instance()
    start_time = time.time()

    try:
        resolved_path = policy.validate_path(path, write=False)
    except SecurityViolation as sv:
        duration_ms = (time.time() - start_time) * 1000
        logger.log(
            action="read_file",
            params={"path": path},
            status="blocked",
            duration_ms=duration_ms,
            error=str(sv),
        )
        return {"success": False, "error": str(sv), "path": path}

    if not resolved_path.exists():
        duration_ms = (time.time() - start_time) * 1000
        err = f"File not found: {resolved_path}"
        logger.log(
            action="read_file",
            params={"path": path},
            status="failed",
            duration_ms=duration_ms,
            error=err,
        )
        return {"success": False, "error": err, "path": str(resolved_path)}

    if not resolved_path.is_file():
        duration_ms = (time.time() - start_time) * 1000
        err = f"Target path is not a regular file: {resolved_path}"
        logger.log(
            action="read_file",
            params={"path": path},
            status="failed",
            duration_ms=duration_ms,
            error=err,
        )
        return {"success": False, "error": err, "path": str(resolved_path)}

    file_size = resolved_path.stat().st_size
    if file_size > max_bytes:
        duration_ms = (time.time() - start_time) * 1000
        err = f"File size ({file_size} bytes) exceeds limit ({max_bytes} bytes)."
        logger.log(
            action="read_file",
            params={"path": path, "size": file_size},
            status="failed",
            duration_ms=duration_ms,
            error=err,
        )
        return {
            "success": False,
            "error": err,
            "path": str(resolved_path),
            "size_bytes": file_size,
        }

    try:
        with open(resolved_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(max_bytes)

        duration_ms = (time.time() - start_time) * 1000
        logger.log(
            action="read_file",
            params={"path": path},
            status="executed",
            duration_ms=duration_ms,
            output_summary=f"Read {len(content)} characters from {resolved_path}",
        )
        return {
            "success": True,
            "path": str(resolved_path),
            "size_bytes": file_size,
            "content": content,
        }
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        err = f"Error reading file {resolved_path}: {e}"
        logger.log(
            action="read_file",
            params={"path": path},
            status="failed",
            duration_ms=duration_ms,
            error=err,
        )
        return {"success": False, "error": err, "path": str(resolved_path)}


def write_file_content(
    path: str,
    content: str,
    append: bool = False,
) -> Dict[str, Any]:
    """Write or append text content to a file within the sandboxed directories.

    Args:
        path: Path to the target file.
        content: String content to write.
        append: If True, append to existing content instead of overwriting.

    Returns:
        Dict with status, path, and bytes written.
    """
    policy = SecurityPolicy.get_instance()
    logger = AuditLogger.get_instance()
    start_time = time.time()

    try:
        resolved_path = policy.validate_path(path, write=True)
    except SecurityViolation as sv:
        duration_ms = (time.time() - start_time) * 1000
        logger.log(
            action="write_file",
            params={"path": path, "append": append, "content_len": len(content)},
            status="blocked",
            duration_ms=duration_ms,
            error=str(sv),
        )
        return {"success": False, "error": str(sv), "path": path}

    try:
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with open(resolved_path, mode, encoding="utf-8") as f:
            f.write(content)

        bytes_written = len(content.encode("utf-8"))
        duration_ms = (time.time() - start_time) * 1000

        logger.log(
            action="write_file",
            params={"path": path, "append": append, "bytes_written": bytes_written},
            status="executed",
            duration_ms=duration_ms,
            output_summary=f"Wrote {bytes_written} bytes to {resolved_path} (mode={mode})",
        )
        return {
            "success": True,
            "path": str(resolved_path),
            "bytes_written": bytes_written,
            "append": append,
        }
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        err = f"Error writing file {resolved_path}: {e}"
        logger.log(
            action="write_file",
            params={"path": path, "append": append},
            status="failed",
            duration_ms=duration_ms,
            error=err,
        )
        return {"success": False, "error": err, "path": str(resolved_path)}


def list_directory(
    path: str = ".",
) -> Dict[str, Any]:
    """List entries inside a directory within the sandbox.

    Args:
        path: Directory path to inspect (defaults to current working directory).

    Returns:
        Dict with entries containing name, type, size, and modified timestamp.
    """
    policy = SecurityPolicy.get_instance()
    logger = AuditLogger.get_instance()
    start_time = time.time()

    try:
        resolved_path = policy.validate_path(path, write=False)
    except SecurityViolation as sv:
        duration_ms = (time.time() - start_time) * 1000
        logger.log(
            action="list_dir",
            params={"path": path},
            status="blocked",
            duration_ms=duration_ms,
            error=str(sv),
        )
        return {"success": False, "error": str(sv), "path": path, "entries": []}

    if not resolved_path.exists():
        duration_ms = (time.time() - start_time) * 1000
        err = f"Directory not found: {resolved_path}"
        logger.log(
            action="list_dir",
            params={"path": path},
            status="failed",
            duration_ms=duration_ms,
            error=err,
        )
        return {"success": False, "error": err, "path": str(resolved_path), "entries": []}

    if not resolved_path.is_dir():
        duration_ms = (time.time() - start_time) * 1000
        err = f"Path is not a directory: {resolved_path}"
        logger.log(
            action="list_dir",
            params={"path": path},
            status="failed",
            duration_ms=duration_ms,
            error=err,
        )
        return {"success": False, "error": err, "path": str(resolved_path), "entries": []}

    try:
        entries: List[Dict[str, Any]] = []
        for item in resolved_path.iterdir():
            try:
                stat = item.stat()
                is_dir = item.is_dir()
                entries.append({
                    "name": item.name,
                    "type": "directory" if is_dir else ("symlink" if item.is_symlink() else "file"),
                    "size_bytes": stat.st_size if not is_dir else None,
                    "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                })
            except (PermissionError, FileNotFoundError):
                entries.append({
                    "name": item.name,
                    "type": "unknown",
                    "size_bytes": None,
                    "modified": None,
                })

        # Sort: directories first, then alphabetical by name
        entries.sort(key=lambda x: (0 if x["type"] == "directory" else 1, x["name"].lower()))

        duration_ms = (time.time() - start_time) * 1000
        logger.log(
            action="list_dir",
            params={"path": path},
            status="executed",
            duration_ms=duration_ms,
            output_summary=f"Found {len(entries)} items in {resolved_path}",
        )
        return {
            "success": True,
            "path": str(resolved_path),
            "count": len(entries),
            "entries": entries,
        }
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        err = f"Error listing directory {resolved_path}: {e}"
        logger.log(
            action="list_dir",
            params={"path": path},
            status="failed",
            duration_ms=duration_ms,
            error=err,
        )
        return {"success": False, "error": err, "path": str(resolved_path), "entries": []}
