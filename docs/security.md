# Security Architecture (Safety Layer)

**AI Remote PC Control** is designed with the principle of **Zero-Trust AI Execution**. The system assumes AI agent output can be unpredictable or potentially hazardous, enforcing strict sandboxing and approval barriers.

---

## 1. Security Modes (`security.mode`)

| Mode | Description | Permitted Operations |
|---|---|---|
| `read-only` | Strict Read-Only | `ping`, `read_file`, `list_dir`, `list_processes`, read inspection shell commands (`ls`, `cat`, `uptime`). Writing, modifying, and terminating processes are strictly blocked. |
| `safe-execute` *(Default)* | Sandboxed Whitelist | Operations are restricted to `allowed_directories`. Whitelisted binaries (`ls`, `cat`, `git`, `python`, etc.) execute immediately. Unlisted commands or process kills require explicit human approval (`pending_approval`). |
| `full-control` | Full Access | All commands allowed except globally blacklisted catastrophic patterns. Complete audit logging of all operations. |

---

## 2. File System Sandboxing

All paths are evaluated and resolved via `Path.resolve()` with tilde expansion (`~`) and symbolic link resolution:
- **Path Traversal Protection**: Relative escapes like `../../../../etc/shadow` are resolved to absolute canonical paths and blocked.
- **Allowed Boundaries**: Any access outside `allowed_directories` triggers a `SecurityViolation` and logs a security event.

---

## 3. Command Blacklist (Blocked Patterns)

The following destructive patterns are **blocked unconditionally across all modes**:
- Recursive root deletion: `rm -rf /`, `rm -rf /*`
- Filesystem formatting: `mkfs`, `mkfs.*`
- Direct block device overwrites: `dd if=...`, `> /dev/sda`, `> /dev/nvme*`
- Fork bombs: `:(){ :|:& };:`
- Root permission mutations: `chmod -R 777 /`
- Emergency system shutdowns: `shutdown`, `reboot`, `poweroff`, `init 0`

---

## 4. Human Approval Workflow

When an operation poses potential risk or is not whitelisted:
1. The server queues an approval request with a unique 8-character `approval_id`.
2. The action is held in `pending_approval` state and is not executed.
3. The user or supervisor grants consent using `approve_action(approval_id)`.
4. Approval tokens expire after a configurable timeout (default: 120 seconds).

---

## 5. Audit Logging (`audit.jsonl`)

Every attempt, execution, status, and failure is recorded in JSONL format:
```json
{
  "timestamp": "2026-10-17T12:20:00.000Z",
  "action": "run_command",
  "status": "executed",
  "params": {"command": "ls -la /home/Danya"},
  "duration_ms": 12.4,
  "exit_code": 0,
  "output_summary": "total 48...",
  "error": null,
  "client": "unknown"
}
```
Logs are protected by thread locks and append safely.
