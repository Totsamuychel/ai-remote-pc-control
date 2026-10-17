# Gemini CLI Integration Guide

This guide details how to install and connect the `remote-pc` MCP extension in **Gemini CLI**.

---

## 1. Extension Installation

### Method A: Direct Extension Install (Recommended)
From your terminal, install the extension using the Gemini CLI extension manager:

```bash
gemini extensions install /run/media/Danya/DATA/code/Proj/integrations/gemini
```

To verify installed extensions:
```bash
gemini extensions list
```

---

### Method B: Manual Configuration (`~/.gemini/config.json`)
Add the `remote-pc` entry into `~/.gemini/config.json`:

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

## 2. Remote Setup via SSH or Tailscale

For remote execution across machines:

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

## 3. Test Scenarios for Gemini CLI

Run `gemini` in interactive mode and try:

1. **Ping & Policy Check**:
   > "Connect to `remote-pc` MCP server. Call `ping()` and report back the security mode and allowed directories."

2. **Filesystem Exploration**:
   > "Show the contents of the project folder using `list_dir()` and create a small scratch file `gemini_test.txt`."

3. **Safe Command Execution**:
   > "Run `python --version` and `df -h` on the remote host."

4. **Security Boundary Enforcement**:
   > "Read `/etc/shadow` on the remote PC."  
   > *(Expected: Rejected with security violation error; logged to audit.jsonl).*
