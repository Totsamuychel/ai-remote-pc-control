# Remote PC Control — Gemini CLI Instructions

You are interacting with a remote PC through the `remote-pc` Model Context Protocol (MCP) server.

## Operational Directives:

1. **Protocol Initialization**:
   - Always run `ping()` before executing multi-step tasks to check the remote PC status, security policy mode, and sandboxed root directories.

2. **File Sandbox**:
   - All file reads, writes, and directory inspections must be confined within the reported `allowed_directories`.
   - Never attempt relative traversal (`../`) out of the sandbox.

3. **Command Rules**:
   - In `safe-execute` mode, use whitelisted commands (`ls`, `cat`, `git`, `python`, `node`, `ps`, `df`, etc.).
   - Destructive patterns (`rm -rf /`, formatting, raw block device writes, fork bombs) are globally blocked.
   - If an unlisted command or process termination is requested, the system will return `pending_approval`.

4. **Approval Handling**:
   - When a tool returns `pending_approval` with an `approval_id`:
     - Stop execution. Do NOT loop.
     - Present the `approval_id` and the exact action to the user.
     - Prompt the user to confirm. Once confirmed, execute `approve_action(approval_id="<id>")` and resume the action.

5. **Process Safety**:
   - Never kill system critical PIDs (PID 0, PID 1).
   - Use `list_processes()` with appropriate limits before managing processes.
