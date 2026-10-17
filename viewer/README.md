# AI Remote PC Control — Desktop & Web Viewer (Stage 6)

The **Viewer Application** provides a dedicated, low-latency interface to monitor and interact with the AI-controlled remote computer.

It supports multiple viewing modes:
1. **Electron Desktop Application**: Native, hardware-accelerated desktop viewer window.
2. **Web Browser HUD**: Works out-of-the-box in any modern browser without extra dependencies.
3. **Terminal Live Stream**: High-speed terminal rendering via native Kitty Graphics protocol or universal 24-bit TrueColor Unicode Half-Blocks (`▀`).

---

## Key Features

- **Live WebSocket JPEG Streaming**: Up to 30 FPS screen updates with adaptive frame compression.
- **Real-Time Telemetry HUD**:
  - **FPS**: Instantaneous frames-per-second counter.
  - **Resolution**: Native screen width and height.
  - **RTT**: Round-trip network ping/pong latency.
  - **Bitrate**: Current bandwidth consumption in KB/s.
- **Live AI Action Approvals**: Interactive on-screen banner to inspect and immediately Approve (`y`) or Reject (`n`) sensitive AI actions (clicks, typing, file writes).
- **Stream Controls**: On-the-fly FPS selector (5, 10, 15, 25, 30 FPS) and fullscreen mode (`⛶`).
- **Remote Host Support**: Connects to localhost, local LAN, or across secure mesh networks (such as **Tailscale** `100.x.y.z:8080`).

---

## Directory Structure

```
viewer/
├── package.json          # Node / Electron configuration
├── viewer.py             # Python multi-target desktop launcher
├── src/
│   ├── main.js           # Electron main process (lifecycle & window management)
│   ├── preload.js        # Secure contextBridge preload script
│   ├── index.html        # Modern HTML5 HUD interface
│   ├── styles.css        # Clean dark-mode stylesheet
│   └── renderer.js       # WebSocket client, telemetry & approval handler
└── README.md             # This documentation
```

---

## Quick Start

### 1. Unified Python Launcher (`viewer/viewer.py`)

The launcher automatically detects the best available viewer on your system:

```bash
# Auto mode: Launches Electron if installed, otherwise opens the default web browser
python viewer/viewer.py --host localhost:8080

# Force browser view directly:
python viewer/viewer.py --mode browser --host 100.85.120.45:8080

# Run terminal stream view directly:
python viewer/viewer.py --mode terminal --fps 15

# Host viewer assets locally and connect to a remote host:
python viewer/viewer.py --serve --port 3000 --host 100.85.120.45:8080
```

### 2. Native Electron Desktop App

To install and run the native Electron application:

```bash
cd viewer
npm install
npm start
```

Or run via `npx` without a local install:

```bash
cd viewer
npx electron src/main.js --host=localhost:8080
```

---

## Connecting via Tailscale VPN

When controlling a remote machine securely across the internet:
1. Ensure both your client device and the target machine are joined to the same Tailscale tailnet.
2. Run the streaming server on the remote target:
   ```bash
   python streaming/server.py --host 0.0.0.0 --port 8080
   ```
3. On your local viewer machine, launch:
   ```bash
   python viewer/viewer.py --host 100.x.y.z:8080
   ```
   *(Replace `100.x.y.z` with your remote machine's Tailscale IP address)*.
