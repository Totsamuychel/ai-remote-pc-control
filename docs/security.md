# Security Architecture & Safety Guidelines

**AI Remote PC Control** is engineered around the principle of **Zero-Trust AI Automation**. Because language models can occasionally hallucinate commands or click erroneous UI coordinates, multiple layers of defense are enforced before any mutating operation touches your computer.

---

## 1. Security Modes (`security.mode`)

The system operates under one of three configurable security tiers defined in `agent/config.yaml`:

| Mode | Intended Use | Permitted Operations |
|---|---|---|
| **`read-only`** | Passive Monitoring & Diagnostics | Only non-mutating operations: `read_file`, `list_dir`, `list_processes`, `screenshot`, `list_windows`, `view_terminal`, inspection commands (`ls`, `cat`, `uptime`). All file writing, GUI clicking, typing, and process killing are rejected. |
| **`safe-execute`** *(Default)* | Everyday AI Pair-Programming | Sandboxed filesystem access within `allowed_directories`. Whitelisted safe binaries (`git`, `npm`, `python`, `cargo`) execute immediately. GUI interactions, process kills, and non-whitelisted commands require human approval (`approval_id`). |
| **`full-control`** | Trusted Sandboxed Environments | Unrestricted execution subject only to the **Global Blacklist** and comprehensive JSONL audit logging. |

---

## 2. Global Command Blacklist

The following destructive patterns are **blocked unconditionally** across all modes:

- **Root Filesystem Deletion**: `rm -rf /`, `rm -rf /*`, `rm -rf ~`
- **Filesystem Formatting**: `mkfs`, `mkfs.*`
- **Raw Disk / Partition Overwrites**: `dd if=...`, direct redirects to `/dev/sd*`, `/dev/nvme*`, or Windows `\\.\PhysicalDrive*`
- **Denial of Service / Fork Bombs**: `:(){ :|:& };:`
- **Global Permission Destabilization**: `chmod -R 777 /`, `chmod -R 777 ~`
- **System Shutdown & Reboots**: `shutdown`, `reboot`, `poweroff`, `init 0`

---

## 3. Human Approval Channels

High-risk operations (mouse clicks, typing, killing processes, executing unwhitelisted scripts) require explicit human consent:

1. **Web HUD Banner**: Pops up a warning modal on `http://localhost:8080` or in the Desktop Viewer with **Approve** and **Reject** buttons.
2. **REST API**: External scripts or frontends can approve via `POST /api/approvals/{id}/approve` or `reject`.
3. **Telegram Inline Buttons**: Instant smartphone alert with interactive inline buttons via `@BotFather` integration.
4. **MCP Command**: Local approval via `approve_action(approval_id)`.

Tokens automatically expire after **120 seconds** (configurable in `agent/config.yaml`).

---

## 4. How to Test the Project Safely

When setting up and testing AI Remote PC Control for the first time:

1. **Start in `safe-execute` or `read-only` Mode**:
   Always keep `security.mode: "safe-execute"` in `agent/config.yaml`.
2. **Restricted `allowed_directories`**:
   Set `allowed_directories` only to a disposable test folder:
   ```yaml
   allowed_directories:
     - "/home/Danya/ai_test_sandbox"
     - "/tmp"
   ```
3. **Verify Blacklist Blocking**:
   Ask the AI client: *"Try running `rm -rf /`"*.
   Verify in the output and audit log that the command was immediately blocked with a `SecurityViolation`.
4. **Verify Mandatory Approval for GUI Actions**:
   Ask the AI: *"Click at coordinates 100, 100"*.
   Verify that the action is not performed until you explicitly click **Approve** in the Viewer or Telegram.
5. **Monitor Audit Logs in Real Time**:
   Keep a terminal open running:
   ```bash
   tail -f logs/audit.jsonl | jq .
   ```
