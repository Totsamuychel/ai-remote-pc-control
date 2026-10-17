# Gemini CLI Integration

## 1. Register Extension in Gemini CLI

Install the extension directly into Gemini CLI:

```bash
gemini extensions install /path/to/ai-remote-pc-control/integrations/gemini
```

Or configure the server in `~/.gemini/config.json`:

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

## 2. Verification

```bash
gemini
```

Prompt:
> "Connect to my remote PC via remote-pc MCP server. Call ping(), report security_mode, and list files in the current folder."
