// Desktop Viewer - Client Renderer & WebSocket Management

let ws = null;
let isConnected = false;
let frameCount = 0;
let bytesReceived = 0;
let lastMetricsTime = performance.now();
let pingTimer = null;
let approvalPollTimer = null;
let activeApprovalId = null;

// UI Elements
const hostInput = document.getElementById('host-input');
const btnConnect = document.getElementById('btn-connect');
const btnStop = document.getElementById('btn-stop');
const btnFullscreen = document.getElementById('btn-fullscreen');
const selectFps = document.getElementById('select-fps');
const statusDot = document.getElementById('status-dot');
const connState = document.getElementById('conn-state');
const streamDisplay = document.getElementById('stream-display');
const standbyScreen = document.getElementById('standby-screen');
const valFps = document.getElementById('val-fps');
const valRes = document.getElementById('val-res');
const valRtt = document.getElementById('val-rtt');
const valRate = document.getElementById('val-rate');

// Approval Modal Elements
const approvalModal = document.getElementById('approval-modal');
const approvalText = document.getElementById('approval-text');
const modalApprove = document.getElementById('modal-approve');
const modalReject = document.getElementById('modal-reject');

function connect() {
    if (ws) {
        ws.close();
    }

    const rawHost = hostInput.value.trim() || 'localhost:8080';
    const cleanHost = rawHost.replace(/^https?:\/\//, '').replace(/^wss?:\/\//, '').replace(/\/$/, '');
    const wsUrl = `ws://${cleanHost}/stream`;

    connState.innerText = 'Connecting...';
    statusDot.className = 'status-indicator connecting';

    try {
        ws = new WebSocket(wsUrl);
        ws.binaryType = 'blob';
    } catch (err) {
        alert(`Failed to initialize WebSocket connection: ${err.message}`);
        setDisconnectedState();
        return;
    }

    ws.onopen = () => {
        isConnected = true;
        setConnectedState();

        // Send initial target FPS
        sendControl({ action: 'set_fps', fps: parseInt(selectFps.value) });

        // Start ping/pong latency timer
        pingTimer = setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'ping', t: performance.now() }));
            }
        }, 1000);

        // Start polling approvals
        pollApprovals(cleanHost);
        approvalPollTimer = setInterval(() => pollApprovals(cleanHost), 1500);
    };

    ws.onmessage = (event) => {
        if (typeof event.data === 'string') {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === 'pong') {
                    const rtt = Math.round(performance.now() - msg.t);
                    valRtt.innerText = `${rtt} ms`;
                }
            } catch (e) {}
            return;
        }

        // Render binary frame
        const blob = event.data;
        bytesReceived += blob.size;
        frameCount++;

        const objectUrl = URL.createObjectURL(blob);
        streamDisplay.onload = () => {
            URL.revokeObjectURL(objectUrl);
            valRes.innerText = `${streamDisplay.naturalWidth}x${streamDisplay.naturalHeight}`;
        };
        streamDisplay.src = objectUrl;

        // Update telemetry every second
        const now = performance.now();
        const elapsed = (now - lastMetricsTime) / 1000;
        if (elapsed >= 1.0) {
            valFps.innerText = (frameCount / elapsed).toFixed(1);
            valRate.innerText = `${(bytesReceived / 1024 / elapsed).toFixed(1)} KB/s`;
            frameCount = 0;
            bytesReceived = 0;
            lastMetricsTime = now;
        }
    };

    ws.onclose = () => {
        setDisconnectedState();
    };

    ws.onerror = (err) => {
        console.error('Viewer WebSocket Error:', err);
        setDisconnectedState();
    };
}

function disconnect() {
    if (ws) {
        ws.close();
        ws = null;
    }
    setDisconnectedState();
}

function sendControl(data) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(data));
    }
}

function setConnectedState() {
    connState.innerText = 'Connected';
    statusDot.className = 'status-indicator connected';
    btnConnect.style.display = 'none';
    btnStop.style.display = 'inline-block';
    standbyScreen.style.display = 'none';
    streamDisplay.style.display = 'block';
}

function setDisconnectedState() {
    isConnected = false;
    connState.innerText = 'Disconnected';
    statusDot.className = 'status-indicator';
    btnConnect.style.display = 'inline-block';
    btnStop.style.display = 'none';
    standbyScreen.style.display = 'block';
    streamDisplay.style.display = 'none';

    valFps.innerText = '0.0';
    valRate.innerText = '0 KB/s';
    valRtt.innerText = '0 ms';

    if (pingTimer) clearInterval(pingTimer);
    if (approvalPollTimer) clearInterval(approvalPollTimer);
    approvalModal.style.display = 'none';
}

// Approval Polling & Resolution
async function pollApprovals(host) {
    try {
        const res = await fetch(`http://${host}/api/approvals`);
        if (res.ok) {
            const data = await res.json();
            const pending = data.pending || [];
            if (pending.length > 0) {
                const req = pending[0];
                activeApprovalId = req.id;
                approvalText.innerText = `Action: ${req.action} | Details: ${JSON.stringify(req.details)}`;
                approvalModal.style.display = 'flex';
            } else {
                approvalModal.style.display = 'none';
                activeApprovalId = null;
            }
        }
    } catch (e) {}
}

async function resolveApproval(action) {
    if (!activeApprovalId) return;
    const rawHost = hostInput.value.trim() || 'localhost:8080';
    const cleanHost = rawHost.replace(/^https?:\/\//, '').replace(/^wss?:\/\//, '').replace(/\/$/, '');

    try {
        await fetch(`http://${cleanHost}/api/approvals/${activeApprovalId}/${action}`, { method: 'POST' });
        approvalModal.style.display = 'none';
        activeApprovalId = null;
        pollApprovals(cleanHost);
    } catch (err) {
        alert(`Approval error: ${err.message}`);
    }
}

// Event Listeners
btnConnect.addEventListener('click', connect);
btnStop.addEventListener('click', disconnect);

selectFps.addEventListener('change', () => {
    sendControl({ action: 'set_fps', fps: parseInt(selectFps.value) });
});

btnFullscreen.addEventListener('click', () => {
    const el = document.getElementById('viewport');
    if (!document.fullscreenElement) {
        el.requestFullscreen().catch(err => alert(`Fullscreen error: ${err.message}`));
    } else {
        document.exitFullscreen();
    }
});

modalApprove.addEventListener('click', () => resolveApproval('approve'));
modalReject.addEventListener('click', () => resolveApproval('reject'));

// Connect automatically on Enter in host input
hostInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') connect();
});

// Auto-detect host from URL query params or Electron API
window.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const paramHost = urlParams.get('host');
    const electronHost = window.electronAPI && typeof window.electronAPI.getHostArg === 'function' ? window.electronAPI.getHostArg() : null;
    const targetHost = paramHost || electronHost;

    if (targetHost) {
        hostInput.value = targetHost;
        connect();
    }
});

