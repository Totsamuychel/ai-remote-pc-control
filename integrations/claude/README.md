# Claude Code Integration

## 1. Local Connection (Same Machine)

Add the server configuration to `~/.claude/mcp.json` or project-level `.claude/mcp.json`:

```json
{
  "mcpServers": {
    "remote-pc": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": [
        "/absolute/path/to/agent/main.py",
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

## 2. Remote Connection via SSH / Tailscale

```json
{
  "mcpServers": {
    "remote-pc": {
      "command": "ssh",
      "args": [
        "user@tailscale-ip",
        "source /path/to/venv/bin/activate && python /path/to/agent/main.py --transport stdio"
      ]
    }
  }
}
```

## 3. Verification in Claude Code

Launch Claude Code:
```bash
claude
```

Prompt:
> "Connect to remote-pc MCP server. Run ping() to check status and list files in the project directory."
