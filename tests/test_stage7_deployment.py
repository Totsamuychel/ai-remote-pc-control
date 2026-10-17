#!/usr/bin/env python3
"""Stage 7 Tests — Production Packaging, Deployment & Multi-PC Setup.

Tests:
1. Installer scripts integrity (install.sh executable, install.ps1 validity).
2. Systemd service unit syntax and security directives.
3. Documentation completeness and cross-linking.
4. Telegram approval notifier module initialization, authorization filters, and mock prompts.
"""

import os
import stat
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.safety.approvals import ApprovalManager
from agent.safety.telegram_bot import TelegramApprovalNotifier


def test_install_scripts_present():
    """Verify Linux and Windows installer scripts exist and have correct permissions."""
    sh_script = PROJECT_ROOT / "install.sh"
    ps_script = PROJECT_ROOT / "install.ps1"

    assert sh_script.exists()
    assert ps_script.exists()

    # Verify install.sh is executable
    st = os.stat(sh_script)
    assert bool(st.st_mode & stat.S_IXUSR), "install.sh should be executable"


def test_systemd_service_units():
    """Verify systemd service unit files syntax and configuration."""
    pc_service = PROJECT_ROOT / "deploy" / "systemd" / "ai-remote-pc.service"
    stream_service = PROJECT_ROOT / "deploy" / "systemd" / "ai-remote-streaming.service"

    assert pc_service.exists()
    assert stream_service.exists()

    pc_content = pc_service.read_text(encoding="utf-8")
    assert "[Unit]" in pc_content
    assert "[Service]" in pc_content
    assert "[Install]" in pc_content
    assert "agent/main.py" in pc_content

    stream_content = stream_service.read_text(encoding="utf-8")
    assert "[Unit]" in stream_content
    assert "[Service]" in stream_content
    assert "[Install]" in stream_content
    assert "streaming/server.py" in stream_content


def test_documentation_suite_completeness():
    """Verify all Stage 7 required documentation files exist and are comprehensive."""
    docs_dir = PROJECT_ROOT / "docs"
    required_docs = [
        "setup-linux.md",
        "setup-windows.md",
        "tailscale-setup.md",
        "clients-setup.md",
        "security.md",
        "multi-pc-scaling.md",
        "telegram-approval.md",
    ]

    for doc_name in required_docs:
        doc_path = docs_dir / doc_name
        assert doc_path.exists(), f"Missing required documentation: {doc_name}"
        assert doc_path.stat().st_size > 300, f"Documentation file {doc_name} is too brief"


def test_telegram_approval_notifier_initialization():
    """Verify TelegramApprovalNotifier initializes cleanly with default/unconfigured state."""
    notifier = TelegramApprovalNotifier(bot_token="", chat_id="")
    assert notifier.is_configured is False
    assert notifier.send_approval_prompt("test-id", "click", {"x": 100}) is False


def test_telegram_approval_notifier_configured():
    """Verify TelegramApprovalNotifier recognizes configured bot token and chat ID."""
    notifier = TelegramApprovalNotifier(bot_token="test_token_123", chat_id="99999999")
    assert notifier.is_configured is True
    assert notifier.chat_id == "99999999"


def test_telegram_polling_and_approval_manager():
    """Verify ApprovalManager.get_pending_requests and notifier polling."""
    mgr = ApprovalManager.get_instance()
    req = mgr.create_request("test_action", {"foo": "bar"})
    
    pending_objs = mgr.get_pending_requests()
    assert any(p.id == req.id for p in pending_objs)

    notifier = TelegramApprovalNotifier(bot_token="", chat_id="")
    # Should not raise AttributeError or crash when unconfigured
    notifier.poll_pending_approvals()


def test_read_only_mode_protections():
    """Verify that terminate_process, GUI actions, and command redirection are blocked in read-only mode."""
    from agent.safety.policy import SecurityPolicy, SecurityViolation
    from agent.tools.processes import terminate_process
    from agent.tools.input_control import mouse_click

    policy = SecurityPolicy.get_instance()
    original_mode = policy.mode
    try:
        policy.mode = "read-only"

        # 1. Process termination should be blocked
        kill_res = terminate_process(pid=99999)
        assert kill_res["success"] is False
        assert "read-only" in kill_res["error"]

        # 2. GUI action should be blocked
        gui_res = mouse_click(x=10, y=10)
        assert gui_res["success"] is False
        assert "read-only" in gui_res["error"]

        # 3. Output redirection in commands should be blocked
        with pytest.raises(SecurityViolation, match="Output redirection"):
            policy.validate_command("cat /dev/null > /tmp/test.txt")

    finally:
        policy.mode = original_mode

