"""Automated tests for AI Remote PC Control - Stage 1 (MVP)."""

import json
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from agent.safety.approvals import ApprovalManager
from agent.safety.audit import AuditLogger
from agent.safety.policy import SecurityPolicy, SecurityViolation
from agent.tools.files import list_directory, read_file_content, write_file_content
from agent.tools.processes import list_system_processes, terminate_process
from agent.tools.terminal import execute_terminal_command


def run_tests():
    print("========================================")
    print(" Running Stage 1 MVP Automated Tests")
    print("========================================")

    # 1. Test Policy - Path sandboxing
    print("\n[Test 1] Directory sandboxing...")
    policy = SecurityPolicy.get_instance(config_path=str(PROJECT_ROOT / "agent" / "config.yaml"))

    # Valid path
    valid = policy.validate_path(str(PROJECT_ROOT))
    assert valid.exists(), "Project root should be valid"
    print("  ✓ Allowed path verified:", valid)

    # Traversal attack
    try:
        policy.validate_path("/etc/shadow")
        assert False, "Should have blocked /etc/shadow"
    except SecurityViolation as e:
        print("  ✓ Sandboxing correctly blocked traversal attempt:", e)

    # 2. Test Policy - Command blacklisting
    print("\n[Test 2] Command blacklist enforcement...")
    dangerous_commands = [
        "rm -rf /",
        "rm -rf /*",
        "mkfs.ext4 /dev/sda1",
        "dd if=/dev/zero of=/dev/sda",
        ":(){ :|:& };:",
        "shutdown -h now",
    ]
    for cmd in dangerous_commands:
        try:
            policy.validate_command(cmd)
            assert False, f"Should have blocked dangerous command: {cmd}"
        except SecurityViolation as e:
            print(f"  ✓ Successfully blocked '{cmd}': {e}")

    # 3. Test Terminal Command Execution
    print("\n[Test 3] Safe terminal execution...")
    res = execute_terminal_command("echo 'MCP Remote PC Test'", cwd=str(PROJECT_ROOT))
    assert res["success"] is True, f"Command execution failed: {res}"
    assert "MCP Remote PC Test" in res["stdout"]
    print("  ✓ Safe command output:", res["stdout"].strip(), f"(took {res['duration_ms']}ms)")

    # Test blocked command execution via tool
    res_blocked = execute_terminal_command("rm -rf /")
    assert res_blocked["success"] is False
    assert "blocked by security policy" in res_blocked["error"].lower()
    print("  ✓ Terminal tool prevented execution of dangerous command")

    # 4. Test File Operations
    print("\n[Test 4] File operations (write, read, list)...")
    test_file = str(PROJECT_ROOT / "test_stage1_sample.txt")

    # Write file
    w_res = write_file_content(test_file, "Sample data for MCP Remote PC Control\nLine 2")
    assert w_res["success"] is True, f"Write failed: {w_res}"
    print("  ✓ File write successful:", w_res["bytes_written"], "bytes")

    # Read file
    r_res = read_file_content(test_file)
    assert r_res["success"] is True, f"Read failed: {r_res}"
    assert "Sample data for MCP" in r_res["content"]
    print("  ✓ File read successful:", len(r_res["content"]), "chars read")

    # List directory
    l_res = list_directory(str(PROJECT_ROOT))
    assert l_res["success"] is True
    file_names = [e["name"] for e in l_res["entries"]]
    assert "test_stage1_sample.txt" in file_names
    print(f"  ✓ Directory listed successfully: {l_res['count']} entries found")

    # Clean up test file
    if os.path.exists(test_file):
        os.remove(test_file)
        print("  ✓ Cleaned up test sample file")

    # 5. Test Process Inspection & Protected PID
    print("\n[Test 5] Process monitoring & safety checks...")
    p_res = list_system_processes(limit=5)
    assert p_res["success"] is True
    assert len(p_res["processes"]) > 0
    print(f"  ✓ Process list retrieved: {len(p_res['processes'])} processes listed (top: {p_res['processes'][0]['name']})")

    # Attempt to terminate PID 1
    k_res = terminate_process(pid=1)
    assert k_res["success"] is False
    assert "forbidden" in k_res["error"].lower()
    print("  ✓ System PID 1 termination correctly blocked")

    # 6. Test Approvals
    print("\n[Test 6] Approval workflow...")
    mgr = ApprovalManager.get_instance()
    req = mgr.create_request("test_action", {"param": 123})
    assert mgr.check_status(req.id) == "pending"
    assert mgr.approve(req.id) is True
    assert mgr.check_status(req.id) == "approved"
    print("  ✓ Approval requested and successfully approved for ID:", req.id)

    # 7. Test Audit Logger
    print("\n[Test 7] Audit logger verification...")
    logger = AuditLogger.get_instance()
    entries = logger.get_recent_entries(limit=10)
    assert len(entries) > 0, "Audit log should contain entries from previous tests"
    print(f"  ✓ Audit log is functional: {len(entries)} recent entries verified")
    print(f"  ✓ Latest action logged: {entries[0]['action']} (status: {entries[0]['status']})")

    print("\n========================================")
    print(" ALL STAGE 1 TESTS PASSED SUCCESSFULLY! ")
    print("========================================")

def test_stage1_mvp():
    """Pytest wrapper for Stage 1 test suite."""
    run_tests()


if __name__ == "__main__":
    run_tests()

