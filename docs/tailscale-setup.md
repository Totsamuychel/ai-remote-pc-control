# Tailscale Secure Private Mesh Setup Guide

This guide explains how to connect to your remote PC from anywhere in the world using **[Tailscale](https://tailscale.com/)** — a zero-configuration WireGuard-based mesh VPN that requires **no public IP address, no dynamic DNS, and no router port forwarding**.

---

## 1. Why Tailscale for AI Remote PC Control?

- **Zero Exposure**: Your remote PC never exposes ports (`8000`, `8080`) to the public internet.
- **End-to-End Encryption**: Direct WireGuard tunnel between your client (laptop/phone) and remote PC.
- **Stable 100.x.y.z IP**: Each device receives a persistent private IP address on your personal tailnet.
- **Cross-NAT Traversal**: Seamlessly connects across double NAT, mobile cellular connections (4G/5G), and hotel/office Wi-Fi.

---

## 2. Installing Tailscale

### On Linux (Remote PC & Client)
```bash
# Official one-line installation
curl -fsSL https://tailscale.com/install.sh | sh

# Start and authenticate
sudo tailscale up
```

### On Windows
1. Download and run the installer from [tailscale.com/download/windows](https://tailscale.com/download/windows).
2. Click the Tailscale tray icon and log in with your account (Google, GitHub, Microsoft, Apple).

### On macOS / iOS / Android
Install the official Tailscale app from the App Store / Google Play and authenticate.

---

## 3. Finding Your Remote Tailscale IP

Once authenticated, find your machine's private Tailscale IP:

```bash
# On Linux / macOS:
tailscale ip -4

# Output example:
# 100.85.120.45
```

Or check your [Tailscale Admin Console](https://login.tailscale.com/admin/machines).

---

## 4. Configuring AI Remote PC Control for Tailscale

### Step 1: Start the MCP Server on the Remote PC
Configure the MCP server to listen on all interfaces or specifically your Tailscale IP:

```bash
# In your remote PC terminal:
cd ai-remote-pc-control
source agent/.venv/bin/activate

# Run MCP server in SSE mode on port 8000:
python agent/main.py --transport sse --host 0.0.0.0 --port 8000
```

### Step 2: Start the Screen Streaming Server
```bash
# In another terminal or systemd service:
python streaming/server.py --host 0.0.0.0 --port 8080
```

---

## 5. Connecting AI Clients over Tailscale

Suppose your remote PC's Tailscale IP is `100.85.120.45`.

### 1. Claude Code
In your local Claude Code configuration (`~/.claude/claude_desktop_config.json` or project `mcp.json`):

```json
{
  "mcpServers": {
    "remote-pc": {
      "url": "http://100.85.120.45:8000/sse"
    }
  }
}
```

### 2. Gemini CLI
In your local Gemini CLI settings or extension config:

```json
{
  "name": "remote-pc",
  "transport": "sse",
  "url": "http://100.85.120.45:8000/sse"
}
```

### 3. Antigravity CLI
In `mcp.json` or `~/.gemini/antigravity-cli/mcp.json`:

```json
{
  "mcpServers": {
    "remote-pc": {
      "transport": "sse",
      "url": "http://100.85.120.45:8000/sse"
    }
  }
}
```

### 4. Viewing the Remote Screen
On your local computer:

```bash
# Auto Desktop Viewer
python viewer/viewer.py --host 100.85.120.45:8080

# Or open in your favorite web browser:
# http://100.85.120.45:8080/
```

---

## 6. Security & Access Control Lists (ACLs)

Tailscale allows you to restrict which devices can communicate with your remote PC.

In the [Tailscale ACL Editor](https://login.tailscale.com/admin/acls):

```json
{
  "acls": [
    {
      "action": "accept",
      "src": ["tag:ai-client"],
      "dst": ["tag:ai-host:8000", "tag:ai-host:8080"]
    }
  ],
  "tagOwners": {
    "tag:ai-client": ["autogroup:admin"],
    "tag:ai-host": ["autogroup:admin"]
  }
}
```

This ensures only authorized client devices tagged with `tag:ai-client` can communicate with your MCP agent and streaming server.
