# Setup & Deployment Guide (Windows)

## 1. System Requirements

- Windows 10 / Windows 11 (64-bit)
- Python 3.10+ (added to system `PATH`)
- PowerShell 7+ or Windows Terminal

## 2. Virtual Environment Setup

Open PowerShell in the project directory:

```powershell
cd agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> **Note:** If script execution is disabled by default, run:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

## 3. Configuration

In `agent/config.yaml`, configure Windows paths for sandboxing:

```yaml
security:
  mode: "safe-execute"
  allowed_directories:
    - "C:\\Users\\User"
    - "C:\\Users\\User\\AppData\\Local\\Temp"
    - "D:\\Projects"
```

## 4. Running the Server

### Stdio Transport:
```powershell
python main.py --transport stdio
```

### SSE Transport (Network):
```powershell
python main.py --transport sse --host 0.0.0.0 --port 8000
```
