# AI Remote PC Control

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge&logo=python" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/MCP-FastMCP-6366f1?style=for-the-badge" alt="MCP FastMCP" />
  <img src="https://img.shields.io/badge/Security-Zero--Trust%20Sandbox-green?style=for-the-badge" alt="Zero-Trust" />
  <img src="https://img.shields.io/badge/Status-Stage%201%20MVP-success?style=for-the-badge" alt="Stage 1 MVP" />
  <img src="https://img.shields.io/badge/License-MIT-orange?style=for-the-badge" alt="License" />
</p>

> **Secure, sandboxed Remote PC Control server powered by the Model Context Protocol (MCP).**  
> Seamlessly connect terminal AI agents (**Gemini CLI**, **Claude Code**, **Antigravity CLI**) to manage remote machines over private networks (Tailscale, WireGuard, SSH) without compromising security.

---

## 🌟 Highlights

- ⚡ **Remote Command Execution** (`run_command`): Subprocess execution with strict timeouts, directory constraints, and execution benchmarking.
- 📁 **Filesystem Sandboxing** (`read_file`, `write_file`, `list_dir`): Sandboxed read and write access with strict Path Traversal (`../`) prevention.
- 🔍 **Process Monitoring** (`list_processes`, `kill_process`): Real-time resource usage inspection with protection for system-critical PIDs (PID 0, 1, self).
- 🛡️ **Zero-Trust Safety Layer**:
  - Regex blacklist for destructive commands (`rm -rf /`, `mkfs`, partition writes, fork bombs).
  - Configurable binary whitelist for `safe-execute` mode.
  - Three distinct security modes: `read-only`, `safe-execute`, and `full-control`.
- 🤝 **Human-in-the-Loop Approvals**: High-risk actions automatically generate temporary approval tokens (`approval_id`) requiring human consent before execution.
- 📜 **Structured Audit Log**: Every tool call, attempted operation, status, duration, and output summary is logged to `logs/audit.jsonl`.
- 🔌 **Dual Transport Support**:
  - `stdio`: Direct execution or encapsulated within SSH tunnels.
  - `sse` (Server-Sent Events): Direct HTTP/JSON-RPC communication across private mesh networks (Tailscale).

---

## 🏗️ Architecture

```mermaid
flowchart LR
    subgraph Client["AI Client"]
        Agent["Claude Code / Gemini CLI"]
    end

    subgraph Network["Secure Transport"]
        Tunnel["Tailscale / SSH Tunnel / stdio"]
    end

    subgraph Host["Remote Target PC"]
        Server["FastMCP Server"]
        Policy["Security Policy & Sandbox"]
        Audit["JSONL Audit Log"]
        Tools["Tools: Terminal | Files | Processes"]
    end

    Agent <-->|JSON-RPC| Tunnel
    Tunnel <--> Server
    Server --> Policy
    Policy -->|Validated| Tools
    Tools --> Audit
```

---

## 📂 Repository Structure

```text
ai-remote-pc-control/
├── README.md                  # Project overview and documentation
├── architecture.md            # In-depth architectural design
├── .env.example               # Environment variables template
├── docker-compose.yml         # Containerized server configuration
├── agent/                     # Core MCP Agent
│   ├── main.py                # CLI runner (stdio and SSE support)
│   ├── mcp_server.py          # FastMCP server and tool registrations
│   ├── config.yaml            # Security policies, whitelists, and paths
│   ├── requirements.txt       # Python dependencies
│   ├── safety/                # Security subsystem
│   │   ├── policy.py          # Path sandboxing and command validation
│   │   ├── approvals.py       # Human confirmation workflow
│   │   └── audit.py           # Structured JSONL audit logging
│   └── tools/                 # Execution tools
│       ├── terminal.py        # Sandboxed shell commands
│       ├── files.py           # Sandboxed file operations
│       └── processes.py       # Process inspection and termination
├── docs/                      # Documentation guides
│   ├── setup-linux.md         # Linux setup instructions
│   ├── setup-windows.md       # Windows setup instructions
│   └── security.md            # Detailed security architecture
├── integrations/              # AI assistant client configurations
│   ├── claude/                # Claude Code integration
│   └── gemini/                # Gemini CLI extension
├── streaming/                 # Screen streaming module (Stage 4)
├── viewer/                    # Screen viewer application (Stage 6)
└── tests/                     # Test suite
    └── test_stage1.py         # Automated validation test
```

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.10+** (tested on 3.11, 3.12, 3.13, 3.14)
- **Linux** or **Windows**

### 2. Installation

Clone repository and prepare the virtual environment:

```bash
git clone https://github.com/Totsamuychel/ai-remote-pc-control.git
cd ai-remote-pc-control/agent

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configuration

Review `agent/config.yaml` to ensure your allowed directories and execution mode match your needs:

```yaml
security:
  mode: "safe-execute" # Options: read-only | safe-execute | full-control
  allowed_directories:
    - "/home/user"
    - "/tmp"
```

### 4. Run the Server

#### Option A: `stdio` mode (Local or through SSH tunnel)
```bash
python main.py --transport stdio
```

#### Option B: `sse` mode (Over private VPN / Tailscale)
```bash
python main.py --transport sse --host 0.0.0.0 --port 8000
```

---

## 🔌 Connecting AI Assistants

### Claude Code (`~/.claude/mcp.json` or project `.claude/mcp.json`)

```json
{
  "mcpServers": {
    "remote-pc": {
      "command": "/path/to/ai-remote-pc-control/agent/.venv/bin/python",
      "args": [
        "/path/to/ai-remote-pc-control/agent/main.py",
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

*For SSH tunneling:*
```json
{
  "mcpServers": {
    "remote-pc": {
      "command": "ssh",
      "args": [
        "user@tailscale-ip",
        "source /path/to/.venv/bin/activate && python /path/to/agent/main.py --transport stdio"
      ]
    }
  }
}
```

### Gemini CLI (`~/.gemini/config.json`)

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

---

## 🛠️ MCP Tools Reference

| Tool | Parameters | Description | Safety Behavior |
|---|---|---|---|
| `ping` | — | Check server connectivity and active security mode | Public |
| `run_command` | `command`, `cwd`, `timeout`, `approval_id` | Execute shell command within allowed working directory | Sandboxed; checks blacklist & whitelist |
| `read_file` | `path`, `max_bytes` | Read file contents (up to 2MB by default) | Sandbox boundary enforced |
| `write_file` | `path`, `content`, `append` | Create or modify file | Blocked in `read-only`; sandbox checked |
| `list_dir` | `path` | List files and metadata inside directory | Sandbox boundary enforced |
| `list_processes` | `limit`, `sort_by` | Inspect running system processes | Read-only |
| `kill_process` | `pid`, `force`, `approval_id` | Terminate process by PID | Protected PIDs guarded (PID 0, 1, self) |
| `pending_approvals`| — | List actions held for human review | Inspection |
| `approve_action` | `approval_id` | Approve held operation | Token authenticated |
| `screenshot` | `output_path`, `quality`, `format` | Capture desktop screenshot to temp file | Multi-platform (Wayland & X11) |
| `list_windows` | — | List all open application windows and metadata | Desktop window inspection |
| `focus_window` | `title` | Switch active focus to a specific application window | Window focus dispatcher |
| `view_terminal` | `cols` | Render current desktop screen directly into terminal | 24-bit TrueColor ANSI Half-Block |
| `click` | `x`, `y`, `button`, `approval_id` | Click mouse button at coordinates | Mandatory `require_approval` |
| `double_click` | `x`, `y`, `approval_id` | Double-click left mouse button | Mandatory `require_approval` |
| `type_text` | `text`, `approval_id` | Type text into currently active window | Mandatory `require_approval` |
| `press_key` | `key`, `approval_id` | Press special or standard keyboard key | Mandatory `require_approval` |
| `scroll` | `amount`, `x`, `y`, `approval_id` | Scroll mouse wheel vertically | Mandatory `require_approval` |

---

## 📺 Live Screen Streaming & Terminal Viewing

### 1. Web Viewer (Browser)
Launch the FastAPI WebSocket streaming service:
```bash
python streaming/server.py --host 0.0.0.0 --port 8080
```
Open **http://localhost:8080** (or `http://tailscale-ip:8080`) in any browser to view the real-time stream with HUD telemetry (FPS, Latency, Resolution, Data Rate) and stream controls.

### 2. Live Terminal Viewer (Directly in Console)
View the desktop stream live inside your terminal:
```bash
# Continuous live stream in terminal
python streaming/terminal_viewer.py --fps 10

# Single snapshot in terminal
python streaming/terminal_viewer.py --once
```
- **Kitty Terminal**: Uses high-resolution Kitty Graphics Protocol (`kitten icat`).
- **All other terminals**: Uses universal 24-bit TrueColor Unicode Half-Blocks (`▀`).

---

## 🛡️ Security Model

| Security Mode | Allowed Operations |
|---|---|
| **`read-only`** | Diagnostic inspection only. `read_file`, `list_dir`, `list_processes`, `screenshot`, `list_windows`, `view_terminal`, safe inspection commands (`ls`, `cat`, `uptime`). No mutations. |
| **`safe-execute`** *(Default)* | Sandboxed file access. Whitelisted commands execute seamlessly. Unknown binaries or process termination require approval (`approval_id`). |
| **`full-control`** | Unrestricted command execution with blacklist filtering and comprehensive JSONL audit logging. |

### Global Blacklist
The following commands are **unconditionally blocked**:
- `rm -rf /`, `rm -rf /*`
- `mkfs`, `mkfs.*`
- `dd if=...`, direct disk overwrites (`> /dev/sda`)
- Fork bombs (`:(){ :|:& };:`)
- `chmod -R 777 /`
- Emergency shutdowns (`shutdown`, `reboot`, `poweroff`)

---

## 🧪 Testing

Run the automated test suite across all implemented stages:

```bash
# Run Stage 1 MVP tool & safety tests
python3 tests/test_stage1.py

# Run Stage 2 Client integration & scenario tests
python3 tests/test_stage2_client.py

# Run Stage 3 Screen capture & window management tests
python3 tests/test_stage3_screen.py

# Run Stage 4 Screen streaming & terminal viewer tests
python3 tests/test_stage4_streaming.py

# Run Stage 5 GUI automation & approval enforcement tests
python3 tests/test_stage5_gui.py

# Run Stage 6 Desktop & Web Viewer tests
python3 -m pytest tests/test_stage6_viewer.py

# Run complete test suite (all 27 tests across Stages 1-6)
python3 -m pytest tests/ -v
```

Expected output:
```text
============================== 27 passed in 2.67s ==============================
```

---

## 🖥️ Stage 6: Desktop & Web Viewer

Launch the viewer client in your preferred environment:

```bash
# Auto mode: Launches Electron if installed, otherwise opens your default web browser
python viewer/viewer.py --host localhost:8080

# Force browser view directly:
python viewer/viewer.py --mode browser --host 100.x.y.z:8080

# Run terminal stream view directly:
python viewer/viewer.py --mode terminal --fps 15

# Host viewer assets locally and connect to a remote target:
python viewer/viewer.py --serve --port 3000 --host 100.x.y.z:8080

# Native Electron App:
cd viewer && npm install && npm start
```

---

## 🗺️ Roadmap

- [x] **Stage 1: MVP** — Core FastMCP server, terminal commands, file sandboxing, process inspection, safety policy, and audit logging.
- [x] **Stage 2: Client Integration** — Seamless configuration for Claude Code, Gemini CLI, and Antigravity CLI, agent system prompts, and scenario validation.
- [x] **Stage 3: Screen & Windows** — Desktop screenshot capture (Wayland/grim & cross-platform mss), window enumeration (Hyprland, Sway, X11, Windows), and focus switching.
- [x] **Stage 4: Real-Time Streaming** — WebSocket video stream via FastAPI, interactive HTML5 web player, and live Terminal Viewer (Kitty HD + ANSI TrueColor).
- [x] **Stage 5: GUI Control** — Mouse/keyboard automation with mandatory human approval (Web UI banner, CLI approval, and MCP token).
- [x] **Stage 6: Viewer App** — Cross-platform Electron desktop app & unified Python launcher with real-time telemetry (FPS, RTT, Bitrate) and interactive approval modal.
- [ ] **Stage 7: Production Packaging** — Systemd services, zero-config installers, and Tailscale VPN orchestration.


---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
