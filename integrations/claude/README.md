# Claude Code Integration Guide

This guide walks through connecting **Claude Code** to the `remote-pc` MCP server.

---

## 1. Local Connection (Same Machine)

If Claude Code runs on the same machine where the agent is installed:

### Step 1: Add MCP Configuration
Add the server entry to your Claude Code global configuration (`~/.claude/mcp.json`) or project configuration (`.claude/mcp.json`):

```json
{
  "mcpServers": {
    "remote-pc": {
      "command": "/run/media/Danya/DATA/code/Proj/agent/.venv/bin/python",
      "args": [
        "/run/media/Danya/DATA/code/Proj/agent/main.py",
        "--transport",
        "stdio"
      ],
      "env": {
        "SECURITY_MODE": "safe-execute"
      }
    }
  }
}
```

Or run via the Claude Code CLI:
```bash
claude mcp add remote-pc /run/media/Danya/DATA/code/Proj/agent/.venv/bin/python /run/media/Danya/DATA/code/Proj/agent/main.py --transport stdio
```

---

## 2. Remote Connection via SSH Tunnel (Different Machines)

If Claude Code runs on your laptop and the MCP agent is running on your remote PC:

```json
{
  "mcpServers": {
    "remote-pc": {
      "command": "ssh",
      "args": [
        "-C",
        "user@tailscale-ip-or-hostname",
        "/run/media/Danya/DATA/code/Proj/agent/.venv/bin/python /run/media/Danya/DATA/code/Proj/agent/main.py --transport stdio"
      ]
    }
  }
}
```

---

## 3. Remote Connection via SSE (Private Mesh / Tailscale)

1. On the remote PC, run the agent in SSE daemon mode:
```bash
python /run/media/Danya/DATA/code/Proj/agent/main.py --transport sse --host 0.0.0.0 --port 8000
```

2. In Claude Code configuration, specify the SSE URL:
```json
{
  "mcpServers": {
    "remote-pc": {
      "url": "http://tailscale-remote-ip:8000/sse"
    }
  }
}
```

---

## 4. System Prompt Setup

Copy [`integrations/claude/CLAUDE.md`](CLAUDE.md) into your Claude Code workspace or add its contents to your project's custom instructions so Claude adheres to sandboxing and approval rules.

---

## 5. Verification Test Scenarios

Launch Claude Code and test the following prompts:

### Scenario 1: Health Check & Mode Verification
> **Prompt:** "Check remote-pc connection using `ping()`. What is the security mode and allowed directories?"  
> **Expected:** Confirms `pong`, displays `security_mode: "safe-execute"`, and lists allowed paths.

### Scenario 2: File Creation & Inspection
> **Prompt:** "Show me the files in the project folder and create a test note named `remote_test.txt` with the text 'Hello from Claude Code'."  
> **Expected:** Uses `list_dir()` and `write_file()`. Confirms bytes written.

### Scenario 3: Whitelisted Command
> **Prompt:** "Run `uname -a` and `git status` on the remote PC."  
> **Expected:** Executes immediately via `run_command()`, logs output into `logs/audit.jsonl`.

### Scenario 4: Blacklisted Command Safety Check
> **Prompt:** "Execute `rm -rf /` on the remote machine."  
> **Expected:** Blocked by `SecurityPolicy`. Returns error without executing.
