"""Approval management system for AI Remote PC Control.

Handles high-risk actions requiring explicit human approval. Actions are queued
as pending approval items with unique IDs, timeouts, and review capabilities.
"""

import threading
import time
import uuid
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass
class PendingApproval:
    id: str
    action: str
    details: Dict[str, Any]
    created_at: float
    timeout_seconds: float
    status: str = "pending"  # pending | approved | rejected | expired

    @property
    def is_expired(self) -> bool:
        return time.time() > (self.created_at + self.timeout_seconds)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["is_expired"] = self.is_expired
        return d


class ApprovalManager:
    """Thread-safe manager for operation approvals."""

    _instance: Optional["ApprovalManager"] = None
    _lock = threading.Lock()

    def __init__(self, default_timeout: float = 120.0):
        self.default_timeout = default_timeout
        self._approvals: Dict[str, PendingApproval] = {}
        self._access_lock = threading.Lock()

    @classmethod
    def get_instance(cls, default_timeout: float = 120.0) -> "ApprovalManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(default_timeout=default_timeout)
            return cls._instance

    def create_request(
        self,
        action: str,
        details: Dict[str, Any],
        timeout: Optional[float] = None,
    ) -> PendingApproval:
        """Create a new pending approval request."""
        approval_id = str(uuid.uuid4())[:8]
        req = PendingApproval(
            id=approval_id,
            action=action,
            details=details,
            created_at=time.time(),
            timeout_seconds=timeout or self.default_timeout,
            status="pending",
        )
        with self._access_lock:
            self._approvals[approval_id] = req
        return req

    def approve(self, approval_id: str) -> bool:
        """Mark a pending request as approved."""
        with self._access_lock:
            req = self._approvals.get(approval_id)
            if not req:
                return False
            if req.is_expired:
                req.status = "expired"
                return False
            req.status = "approved"
            return True

    def reject(self, approval_id: str) -> bool:
        """Mark a pending request as rejected."""
        with self._access_lock:
            req = self._approvals.get(approval_id)
            if not req:
                return False
            req.status = "rejected"
            return True

    def check_status(self, approval_id: str) -> Optional[str]:
        """Check current status of an approval request."""
        with self._access_lock:
            req = self._approvals.get(approval_id)
            if not req:
                return None
            if req.status == "pending" and req.is_expired:
                req.status = "expired"
            return req.status

    def list_pending(self) -> List[Dict[str, Any]]:
        """List all currently active pending requests."""
        with self._access_lock:
            active = []
            for req in self._approvals.values():
                if req.status == "pending":
                    if req.is_expired:
                        req.status = "expired"
                    else:
                        active.append(req.to_dict())
            return active
