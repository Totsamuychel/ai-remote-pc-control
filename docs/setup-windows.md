# Windows Deployment & Administration Guide

This guide covers installing, configuring, and operating **AI Remote PC Control** on Windows 10 and Windows 11 (64-bit).

---

## 1. Quick Automated Installation

Open PowerShell as Administrator (or standard user) and run:

```powershell
git clone https://github.com/Totsamuychel/ai-remote-pc-control.git
cd ai-remote-pc-control

# Enable PowerShell script execution if restricted
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Run the automated installer
.\install.ps1
```

---

## 2. Windows Specific Dependencies

The installer automatically installs:
- `mss`: Ultra-fast multi-monitor screen grabber using Windows GDI / DirectX Desktop Duplication API.
- `Pillow`: Image compression and encoding engine.
- `pywin32`: Native Windows API bindings for window enumeration (`EnumWindows`), window focusing (`SetForegroundWindow`), and SendInput for mouse/keyboard automation.

---

## 3. Configuration (`agent/config.yaml` & `.env`)

On Windows, use escaped backslashes or forward slashes in path configurations:

```yaml
security:
  mode: "safe-execute"
  allowed_directories:
    - "C:/Users/User"
    - "C:/Users/User/AppData/Local/Temp"
    - "D:/Projects"
```

In `.env`:
```env
MCP_TRANSPORT=sse
MCP_HOST=0.0.0.0
MCP_PORT=8000
```

---

## 4. Running Automatically on Windows Startup

To run the services quietly in the background without keeping a terminal open:

### Option A: Windows Task Scheduler (Recommended)
1. Open **Task Scheduler** (`taskschd.msc`).
2. Click **Create Task...** -> Name: `AI Remote PC Agent`.
3. Check **Run only when user is logged on** (required for desktop screen access).
4. **Trigger**: At log on of any user.
5. **Action**: Start a program:
   - Program/script: `powershell.exe`
   - Arguments: `-WindowStyle Hidden -ExecutionPolicy Bypass -File .\agent\.venv\Scripts\python.exe agent\main.py --transport sse --host 0.0.0.0 --port 8000`
   - Start in: `C:\path\to\ai-remote-pc-control`

### Option B: Windows Startup Folder
Create a shortcut or batch script in `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`:

```bat
@echo off
start /B .\agent\.venv\Scripts\python.exe agent\main.py --transport sse --host 0.0.0.0 --port 8000
start /B .\agent\.venv\Scripts\python.exe streaming\server.py --host 0.0.0.0 --port 8080
```

---

## 5. Windows Defender & Firewall

When using **Tailscale**, Windows Firewall will automatically trust connections incoming from the private Tailscale interface (`Tailscale` network adapter).

If connecting across your local LAN without Tailscale:
```powershell
New-NetFirewallRule -DisplayName "AI Remote PC Control (MCP)" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "AI Remote PC Control (Stream)" -Direction Inbound -LocalPort 8080 -Protocol TCP -Action Allow
```
