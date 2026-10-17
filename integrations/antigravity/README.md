# Antigravity CLI Integration Guide

This guide details how to integrate `remote-pc` with **Antigravity CLI** (`agy`).

---

## 1. Local Configuration

Add `remote-pc` to your Antigravity configuration file (e.g. `~/.gemini/antigravity-cli/mcp.json` or `.agy/mcp.json`):

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

---

## 2. Remote Configuration via Tailscale / SSH

```json
{
  "mcpServers": {
    "remote-pc": {
      "command": "ssh",
      "args": [
        "-C",
        "user@tailscale-ip",
        "/run/media/Danya/DATA/code/Proj/agent/.venv/bin/python /run/media/Danya/DATA/code/Proj/agent/main.py --transport stdio"
      ]
    }
  }
}
```

---

## 3. Testing with `agy`

Run `agy` and prompt:
> "Check the remote-pc MCP tools. Call ping() and show current status."
