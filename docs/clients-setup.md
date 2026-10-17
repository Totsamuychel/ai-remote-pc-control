# AI Clients Setup & Connection Guide

This guide details how to connect **Claude Code**, **Gemini CLI**, and **Antigravity CLI** to your AI Remote PC Control instance.

---

## 1. Prerequisites

1. Remote PC is running the MCP agent:
   - **Local / SSH stdio**: Executable via python command.
   - **Network / Tailscale SSE**: Listening on `http://<HOST>:8000/sse`.
2. Remote PC is running the streaming server on port `8080` (if screen viewing is desired).

---

## 2. Claude Code Integration

### Option A: Local Stdio Connection (Same Machine or Direct SSH)
Add the following to your project's `.claude/mcp.json` or global `~/.claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "remote-pc": {
      "command": "/path/to/ai-remote-pc-control/agent/.venv/bin/python",
      "args": [
        "/path/to/ai-remote-pc-control/agent/main.py",
        "--transport",
        "stdio"
      ]
    }
  }
}
```

### Option B: Remote SSE Connection (Over Tailscale VPN)
```json
{
  "mcpServers": {
    "remote-pc": {
      "url": "http://100.x.y.z:8000/sse"
    }
  }
}
```

### Recommended Claude Code System Prompt (`CLAUDE.md`)
Place this file in your project root or Claude workspace:

```markdown
You are connected to an AI Remote PC Control server via MCP tools.
Always observe the following rules:
1. First use `list_windows` and `screenshot` or `view_terminal` to understand the desktop state.
2. For GUI actions (clicks, typing, keyboard presses), always inform the user of the exact coordinates and action before executing.
3. High-risk operations (mouse clicks, process termination, file writes) generate an approval request. Instruct the user to approve either via the Web HUD (/api/approvals), Telegram, or CLI prompt.
4. Never attempt destructive commands such as rm -rf /, mkfs, or dd.
```

---

## 3. Gemini CLI Integration

### Extension Configuration
Register the extension by adding `integrations/gemini/gemini-extension.json` or running:

```bash
gemini extension register \
  --name "remote-pc" \
  --url "http://100.x.y.z:8000/sse" \
  --transport "sse"
```

Or configure via `settings.json`:
```json
{
  "extensions": [
    {
      "name": "remote-pc",
      "transport": "sse",
      "url": "http://100.x.y.z:8000/sse",
      "description": "Secure remote PC control and desktop management"
    }
  ]
}
```

---

## 4. Antigravity CLI Integration

In your Antigravity MCP configuration (`~/.gemini/antigravity-cli/mcp.json` or `.mcp.json`):

```json
{
  "mcpServers": {
    "remote-pc": {
      "transport": "sse",
      "url": "http://100.x.y.z:8000/sse"
    }
  }
}
```

---

## 5. End-to-End Test Dialogue

Once your client is connected, try running this sample scenario:

```text
User:
Connect to my remote PC and check its status.

Agent:
I will check the system processes and capture a view of your current desktop.
[Calls list_processes]
Found 142 processes active. System load average is 0.42.
[Calls view_terminal]
[Renders ASCII/Kitty terminal snapshot of the desktop]
Active windows include:
- Kitty Terminal
- Chromium Browser (GitHub)

User:
Open terminal and create a test folder named "demo" in my workspace.

Agent:
[Calls run_command: mkdir -p /home/Danya/demo]
Folder successfully created.
```
