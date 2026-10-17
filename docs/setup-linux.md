# Setup & Deployment Guide (Linux)

## 1. System Requirements

- Linux (Arch, Ubuntu 22.04+, Debian 12+, Fedora 38+)
- Python 3.10+ (recommended: Python 3.11 - 3.14)
- Local network or private VPN (Tailscale, WireGuard)

## 2. Virtual Environment Setup

```bash
cd agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Configuration

Copy environment template and review security configuration:
```bash
cp ../.env.example ../.env
```

Verify `allowed_directories` in `agent/config.yaml`:
```yaml
security:
  mode: "safe-execute"
  allowed_directories:
    - "/home/Danya"
    - "/tmp"
    - "/run/media/Danya/DATA/code/Proj"
```

## 4. Running the Server

### Stdio Transport (Direct CLI or SSH Tunnel):
```bash
python main.py --transport stdio
```

### SSE Transport (Network / Tailscale):
```bash
python main.py --transport sse --host 0.0.0.0 --port 8000
```

## 5. Audit Log Inspection

Monitor activity in real time:
```bash
tail -f agent/logs/audit.jsonl | jq .
```
