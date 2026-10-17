# Remote PC Control — Claude Code Instructions

You are connected to a remote PC via the `remote-pc` Model Context Protocol (MCP) server. Follow these operational guidelines:

## 1. Session Initialization
- At the start of a session or when first addressing the remote host, call `ping()` to check connectivity, determine the active `security_mode` (`read-only`, `safe-execute`, or `full-control`), and verify `allowed_directories`.

## 2. Directory & Path Sandboxing
- All operations (`read_file`, `write_file`, `list_dir`, and `run_command` `cwd`) must be within the sandboxed directories reported by `ping()`.
- Do not use relative path traversal (`../../`) attempting to access root or system paths.
- Default to using the user's home directory or project directory as working directories.

## 3. Safe Command Execution
- In `safe-execute` mode, whitelisted commands (`ls`, `cat`, `git`, `python`, `node`, `npm`, `ps`, `df`, etc.) execute immediately.
- Destructive commands (`rm -rf /`, `mkfs`, partition writes, fork bombs) are globally blocked and will be rejected.
- If an unlisted command is executed, the server will return a `pending_approval` status with an `approval_id`.

## 4. Human Approval Workflow
- When a tool returns `status: "pending_approval"`:
  1. Do NOT retry the exact command in a loop.
  2. Inform the user clearly about the command or action held for approval.
  3. Display the 8-character `approval_id`.
  4. Ask the user for confirmation.
  5. Once approved by the user, call `approve_action(approval_id="<id>")` and then re-execute the original command.

## 5. Process Monitoring & Management
- Always call `list_processes(limit=20, sort_by="cpu")` or `sort_by="memory"` before attempting process termination.
- Never attempt to terminate PID 0 or PID 1 (init/systemd).
- Process termination in `safe-execute` mode requires explicit approval.
