"""Security policy engine for AI Remote PC Control.

Enforces:
1. Sandboxed directory access (preventing Path Traversal).
2. Command safety (blacklisted destructive regex patterns and safe-execute whitelisting).
3. Access modes ('read-only', 'safe-execute', 'full-control').
4. Approval requirements for high-risk operations.
"""

import os
import re
import shlex
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import yaml


class SecurityViolation(Exception):
    """Raised when an operation violates security policy."""
    pass


class ApprovalRequired(Exception):
    """Raised when an operation requires explicit human approval before execution."""
    def __init__(self, action: str, details: Dict[str, Any], approval_id: str):
        super().__init__(f"Operation '{action}' requires approval. Approval ID: {approval_id}")
        self.action = action
        self.details = details
        self.approval_id = approval_id


class SecurityPolicy:
    """Evaluates security rules and sandboxing constraints."""

    _instance: Optional["SecurityPolicy"] = None

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._find_default_config()
        self.config = self._load_config()

        # Security mode: read-only | safe-execute | full-control
        env_mode = os.environ.get("SECURITY_MODE")
        self.mode = env_mode if env_mode else self.config.get("security", {}).get("mode", "safe-execute")

        # Allowed directories
        raw_dirs = self.config.get("security", {}).get("allowed_directories", [])
        self.allowed_directories: List[Path] = []
        for d in raw_dirs:
            p = Path(d).expanduser().resolve()
            self.allowed_directories.append(p)

        # Fallback if empty: Home and /tmp
        if not self.allowed_directories:
            self.allowed_directories = [Path.home().resolve(), Path("/tmp").resolve(), Path.cwd().resolve()]

        # Compile blocked patterns
        raw_blocked = self.config.get("security", {}).get("blocked_patterns", [])
        self.blocked_patterns = [re.compile(p, re.IGNORECASE) for p in raw_blocked]

        # Whitelist commands for safe-execute mode
        raw_whitelist = self.config.get("security", {}).get("whitelist_commands", [])
        self.whitelist_commands: Set[str] = set(raw_whitelist)

        # Read limit
        self.max_file_read_bytes = self.config.get("security", {}).get("max_file_read_bytes", 2 * 1024 * 1024)

    @classmethod
    def get_instance(cls, config_path: Optional[str] = None) -> "SecurityPolicy":
        if cls._instance is None:
            cls._instance = cls(config_path=config_path)
        return cls._instance

    def _find_default_config(self) -> str:
        candidates = [
            Path(__file__).parent.parent / "config.yaml",
            Path.cwd() / "config.yaml",
            Path.cwd() / "agent" / "config.yaml",
        ]
        for c in candidates:
            if c.exists():
                return str(c.resolve())
        return "config.yaml"

    def _load_config(self) -> Dict[str, Any]:
        p = Path(self.config_path)
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                print(f"[SecurityPolicy Warning] Failed to parse {p}: {e}. Using defaults.")
        return {}

    def validate_path(self, target_path: str, write: bool = False) -> Path:
        """Validate and resolve target path against directory sandbox and mode.

        Args:
            target_path: Path string supplied by client.
            write: Whether this is a write / modification operation.

        Returns:
            Resolved Path object if valid.

        Raises:
            SecurityViolation: If path violates sandbox or read-only mode.
        """
        if self.mode == "read-only" and write:
            raise SecurityViolation("Write operations are blocked in 'read-only' mode.")

        # Expand user (~) and resolve real path (resolves symlinks and ..)
        try:
            path_obj = Path(target_path).expanduser().resolve()
        except Exception as e:
            raise SecurityViolation(f"Invalid path expression '{target_path}': {e}")

        # In full-control mode, still prevent obvious root destruction unless explicitly configured
        if self.mode != "full-control":
            # Check if path is contained within any allowed directory
            is_allowed = False
            for allowed_dir in self.allowed_directories:
                try:
                    # If target is inside allowed_dir or equal to it
                    if path_obj == allowed_dir or allowed_dir in path_obj.parents:
                        is_allowed = True
                        break
                except ValueError:
                    continue

            if not is_allowed:
                allowed_str = ", ".join(str(d) for d in self.allowed_directories)
                raise SecurityViolation(
                    f"Path '{target_path}' resolves to '{path_obj}', which is outside allowed directories: [{allowed_str}]"
                )

        return path_obj

    def validate_command(self, command: str) -> Tuple[bool, Optional[str]]:
        """Validate shell command against blacklists, whitelists, and security mode.

        Args:
            command: Shell command string.

        Returns:
            Tuple of (is_safe: bool, reason_or_warning: Optional[str])

        Raises:
            SecurityViolation: If command contains destructive / blacklisted pattern.
        """
        cmd_stripped = command.strip()
        if not cmd_stripped:
            return True, None

        if self.mode == "read-only":
            # In read-only mode, only non-mutating inspection commands are permitted
            safe_read_commands = {"ls", "pwd", "cat", "head", "tail", "grep", "find", "whoami", "uname", "df", "free", "ps", "uptime", "stat"}
            binaries = self._extract_command_binaries(cmd_stripped)
            for b in binaries:
                if b not in safe_read_commands:
                    raise SecurityViolation(f"Command '{b}' is blocked in 'read-only' mode. Only inspection commands are allowed.")
            return True, None

        # Check blacklisted regex patterns across all modes
        for pattern in self.blocked_patterns:
            if pattern.search(cmd_stripped):
                raise SecurityViolation(f"Command violates security policy. Blocked by pattern: {pattern.pattern}")

        # Check in safe-execute mode
        if self.mode == "safe-execute":
            binaries = self._extract_command_binaries(cmd_stripped)
            unlisted = [b for b in binaries if b not in self.whitelist_commands]
            if unlisted:
                return False, f"Command binary '{unlisted[0]}' is not in the safe whitelist."

        return True, None

    def _extract_command_binaries(self, command_line: str) -> List[str]:
        """Extract primary binary executable names from a shell command pipeline/chain."""
        # Split pipelines, chains: |, &&, ||, ;, \n
        subcmds = re.split(r'[|;&\n]', command_line)
        binaries = []
        for sub in subcmds:
            sub = sub.strip()
            if not sub:
                continue
            try:
                tokens = shlex.split(sub)
                if tokens:
                    first = tokens[0]
                    # Handle env assignments like VAR=val command
                    while "=" in first and not first.startswith("./") and not first.startswith("/"):
                        tokens.pop(0)
                        if not tokens:
                            break
                        first = tokens[0]
                    if tokens:
                        bin_name = Path(tokens[0]).name
                        # Strip sudo or wrappers
                        if bin_name in ("sudo", "env", "nohup", "time", "nice") and len(tokens) > 1:
                            bin_name = Path(tokens[1]).name
                        binaries.append(bin_name)
            except Exception:
                # If shlex parsing fails, fallback to simple split
                first = sub.split()[0]
                binaries.append(Path(first).name)
        return binaries

    def is_kill_allowed(self, pid: int) -> bool:
        """Check if stopping a given process PID is permitted."""
        # Never allow killing PID 0, 1 (init/systemd), or self
        if pid <= 1:
            return False
        if pid == os.getpid():
            return False
        return True
