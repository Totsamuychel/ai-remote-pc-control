# Multi-PC Scaling & Fleet Management Guide

This document describes architectural patterns and best practices for scaling **AI Remote PC Control** across multiple physical machines, cloud instances, and edge devices.

---

## 1. Multi-PC Network Topology with Tailscale

When controlling multiple remote PCs, each machine is assigned a distinct hostname and private IP address within your Tailscale mesh VPN:

```
                      ┌──────────────────────┐
                      │ Local AI Client      │
                      │ (Claude/Gemini/AGY)  │
                      └──────────┬───────────┘
                                 │ Tailnet WireGuard Mesh
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│ PC 1: Workstation│   │ PC 2: GPU Server │   │ PC 3: Lab Laptop │
│ 100.85.120.45    │   │ 100.85.120.50    │   │ 100.85.120.62    │
│ (Arch Linux)     │   │ (Ubuntu + CUDA)  │   │ (Windows 11)     │
└──────────────────┘   └──────────────────┘   └──────────────────┘
```

---

## 2. Multi-Host MCP Client Configuration

Modern MCP clients (Claude Code, Gemini CLI, Antigravity CLI) natively support registering multiple MCP servers simultaneously.

### Claude Desktop / Claude Code Multi-Server Config:
```json
{
  "mcpServers": {
    "workstation": {
      "url": "http://100.85.120.45:8000/sse"
    },
    "gpu-server": {
      "url": "http://100.85.120.50:8000/sse"
    },
    "lab-laptop": {
      "url": "http://100.85.120.62:8000/sse"
    }
  }
}
```

The AI agent will see tools namespaced or distinguished by server:
- `workstation_run_command` / `gpu-server_run_command`
- Or can be prompted: *"Run `nvidia-smi` on `gpu-server` and compile the project on `workstation`"*.

---

## 3. Host Switching in Desktop Viewer

The **Desktop Viewer** (`viewer/viewer.py` and Web HUD) allows switching between remote PCs instantaneously:

### Via Command-Line:
```bash
# Connect to GPU Server:
python viewer/viewer.py --host 100.85.120.50:8080

# Connect to Lab Laptop:
python viewer/viewer.py --host 100.85.120.62:8080
```

### Via Viewer UI:
In the top connection bar, simply enter the target IP or hostname (e.g. `gpu-server:8080` if using MagicDNS) and click **Connect**.

---

## 4. Security & Isolation in Multi-PC Environments

1. **Role-Based Security Policies**:
   - Workstation: `security.mode: "safe-execute"`
   - Production / Database servers: `security.mode: "read-only"`
   - Disposable dev containers: `security.mode: "full-control"`
2. **Distinct Approval Channels**:
   - Assign dedicated Telegram bots or distinct group chat topics per machine so approvals are clearly attributed.
3. **Audit Centralization**:
   - Forward `logs/audit.jsonl` from each node to a centralized log aggregator (Vector, FluentBit, or Loki) for organization-wide traceability.
