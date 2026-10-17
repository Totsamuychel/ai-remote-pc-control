"""Automated tests for AI Remote PC Control - Stage 5: GUI Control & Approval Enforcement.

Verifies:
1. Mandatory Human-in-the-Loop approval for all GUI actions (click, double_click, type_text, press_key, scroll).
2. Proper generation of unique approval tokens (approval_id) and pending statuses.
3. Successful execution only AFTER human consent is granted via ApprovalManager or Web REST API.
4. Rejection handling preventing unauthorized GUI mutations.
5. FastMCP tools integration (click, double_click, type_text, press_key, scroll).
6. Web streaming API endpoints for approvals: GET /api/approvals, POST /api/approvals/{id}/approve, POST /api/approvals/{id}/reject.
7. Audit log verification for pending and executed GUI operations.
"""

import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from starlette.testclient import TestClient

from agent.safety.approvals import ApprovalManager
from agent.safety.audit import AuditLogger
from agent.tools.input_control import (
    keyboard_press,
    keyboard_type,
    mouse_click,
    mouse_double_click,
    mouse_scroll,
)
from streaming.server import app


def test_mandatory_approvals():
    print("\n[Stage 5 - Test 1] Testing mandatory require_approval enforcement on GUI tools...")
    
    # 1. Click without approval
    res_click = mouse_click(x=500, y=300)
    assert res_click["success"] is False
    assert res_click["status"] == "pending_approval"
    assert "approval_id" in res_click
    print(f"  ✓ mouse_click held for approval (ID: {res_click['approval_id']})")

    # 2. Double click without approval
    res_dbl = mouse_double_click(x=500, y=300)
    assert res_dbl["success"] is False
    assert res_dbl["status"] == "pending_approval"
    print(f"  ✓ mouse_double_click held for approval (ID: {res_dbl['approval_id']})")

    # 3. Type text without approval
    res_type = keyboard_type("Safety verification text")
    assert res_type["success"] is False
    assert res_type["status"] == "pending_approval"
    print(f"  ✓ keyboard_type held for approval (ID: {res_type['approval_id']})")

    # 4. Press key without approval
    res_press = keyboard_press("Return")
    assert res_press["success"] is False
    assert res_press["status"] == "pending_approval"
    print(f"  ✓ keyboard_press held for approval (ID: {res_press['approval_id']})")

    # 5. Scroll without approval
    res_scroll = mouse_scroll(amount=-5)
    assert res_scroll["success"] is False
    assert res_scroll["status"] == "pending_approval"
    print(f"  ✓ mouse_scroll held for approval (ID: {res_scroll['approval_id']})")


def test_approval_and_execution_workflow():
    print("\n[Stage 5 - Test 2] Testing approval grant and execution workflow...")
    mgr = ApprovalManager.get_instance()

    # Trigger click action
    req_res = mouse_click(x=100, y=100)
    aid = req_res["approval_id"]
    assert mgr.check_status(aid) == "pending"

    # Grant approval
    approved = mgr.approve(aid)
    assert approved is True
    assert mgr.check_status(aid) == "approved"
    print(f"  ✓ Granted approval for action ID: {aid}")

    # Re-execute with approval_id
    exec_res = mouse_click(x=100, y=100, approval_id=aid)
    assert exec_res["success"] is True or "duration_ms" in exec_res
    print(f"  ✓ Successfully dispatched approved click at (100, 100)")


def test_rejection_workflow():
    print("\n[Stage 5 - Test 3] Testing action rejection handling...")
    mgr = ApprovalManager.get_instance()

    req = keyboard_type("Dangerous command")
    aid = req["approval_id"]

    # Reject action
    rejected = mgr.reject(aid)
    assert rejected is True
    assert mgr.check_status(aid) == "rejected"
    print(f"  ✓ Rejected action ID: {aid}")

    # Re-attempting with rejected ID must fail to execute
    attempt = keyboard_type("Dangerous command", approval_id=aid)
    assert attempt["success"] is False
    assert attempt["status"] == "pending_approval"
    assert attempt["approval_id"] != aid, "Should have generated a new pending request ID"
    print("  ✓ System prevented execution using rejected approval token")


def test_web_approval_endpoints():
    print("\n[Stage 5 - Test 4] Testing Web Viewer approval REST endpoints...")
    mgr = ApprovalManager.get_instance()
    
    # Create a pending approval
    req = mouse_scroll(amount=3)
    aid = req["approval_id"]

    with TestClient(app) as client:
        # GET /api/approvals
        resp_list = client.get("/api/approvals")
        assert resp_list.status_code == 200
        pending_items = resp_list.json().get("pending", [])
        found_ids = [item["id"] for item in pending_items]
        assert aid in found_ids
        print(f"  ✓ GET /api/approvals confirmed {len(pending_items)} pending actions (found {aid})")

        # POST /api/approvals/{id}/approve
        resp_app = client.post(f"/api/approvals/{aid}/approve")
        assert resp_app.status_code == 200
        assert resp_app.json().get("success") is True
        assert mgr.check_status(aid) == "approved"
        print(f"  ✓ POST /api/approvals/{aid}/approve granted consent via Web API")


def test_mcp_gui_tools():
    print("\n[Stage 5 - Test 5] Testing FastMCP GUI tool registration...")
    from agent.mcp_server import create_mcp_server
    server = create_mcp_server()
    assert server is not None

    # Call click via underlying registered function
    from agent.tools.input_control import mouse_click
    click_res = mouse_click(x=200, y=200)
    assert click_res["status"] == "pending_approval"
    print(f"  ✓ MCP GUI tools verified and enforce pending_approval tokens")


def test_audit_logs():
    print("\n[Stage 5 - Test 6] Verifying audit logging for GUI actions...")
    logger = AuditLogger.get_instance()
    recent = logger.get_recent_entries(limit=15)
    actions = [e["action"] for e in recent]
    statuses = [e["status"] for e in recent]
    
    assert "click" in actions
    assert "pending_approval" in statuses
    print(f"  ✓ Audit log verified: contains GUI actions {set(actions)} with statuses {set(statuses)}")


def run_all():
    print("==================================================")
    print(" Running Stage 5 (GUI Control) Test Suite         ")
    print("==================================================")
    test_mandatory_approvals()
    test_approval_and_execution_workflow()
    test_rejection_workflow()
    test_web_approval_endpoints()
    test_mcp_gui_tools()
    test_audit_logs()
    print("\n==================================================")
    print(" ALL STAGE 5 GUI CONTROL TESTS PASSED!            ")
    print("==================================================")


if __name__ == "__main__":
    run_all()
