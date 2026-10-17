# Linux Deployment & Administration Guide

This guide covers installing, configuring, and operating **AI Remote PC Control** on Linux systems (Arch Linux, Ubuntu 22.04+, Debian 12+, Fedora 38+).

---

## 1. Quick Automated Installation

Run the automated installer script:

```bash
git clone https://github.com/Totsamuychel/ai-remote-pc-control.git
cd ai-remote-pc-control

# Install environment and dependencies
./install.sh

# Optional: Install and enable background systemd services automatically
./install.sh --systemd
```

---

## 2. Display Server Support: Wayland vs. X11

The system automatically detects your display environment:

### Wayland (Hyprland, Sway, GNOME Wayland, KDE Plasma 6 Wayland)
- **Screenshot Capture**: Uses native `grim` for hardware-accelerated screenshot capture without requiring XWayland.
- **Window Management**: Uses compositor IPC protocols (e.g., `hyprctl` for Hyprland, `swaymsg` for Sway).
- **GUI Input Automation**: Uses `ydotool` or XWayland `xdotool`.

Install dependencies:
```bash
# Arch Linux
sudo pacman -S grim slurp xdotool

# Ubuntu / Debian
sudo apt install grim slurp xdotool

# Fedora
sudo dnf install grim slurp xdotool
```

### X11 (i3, bspwm, XFCE, GNOME X11)
- **Screenshot Capture**: Uses `mss` + `Pillow` or `scrot`.
- **Window Management**: Uses standard `wmctrl` and `xprop`.
- **GUI Input Automation**: Uses `xdotool`.

---

## 3. Configuration (`agent/config.yaml` & `.env`)

Review your sandboxed directory paths:

```yaml
security:
  mode: "safe-execute"
  allowed_directories:
    - "/home/Danya"
    - "/tmp"
    - "/run/media/Danya/DATA/code/Proj"
```

Configure networking and secrets in `.env`:
```env
MCP_TRANSPORT=sse
MCP_HOST=0.0.0.0
MCP_PORT=8000
```

---

## 4. Running as a Systemd Background Service

For unattended 24/7 remote operation, run as a **systemd user service**:

```bash
# Start the MCP Agent
systemctl --user start ai-remote-pc

# Start the Screen Streaming Service
systemctl --user start ai-remote-streaming

# Check service status
systemctl --user status ai-remote-pc
systemctl --user status ai-remote-streaming

# View live journal logs
journalctl --user -u ai-remote-pc -f
```

---

## 5. Troubleshooting Common Issues

### "Cannot open display" or "screenshot failed"
Ensure your systemd service or shell inherits your active display variables:
```bash
echo $WAYLAND_DISPLAY  # Should be e.g. wayland-1
echo $DISPLAY          # Should be e.g. :0
```
In `deploy/systemd/ai-remote-pc.service`, verify `Environment=DISPLAY=:0` matches your active session.

### "Permission denied" during screen capture
Ensure the user has permission to read the compositor socket (typically ensured by being in the active seat or `video`/`input` group).
