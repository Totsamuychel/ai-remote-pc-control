#!/usr/bin/env bash
# AI Remote PC Control — Linux Production Installer
# Sets up Python virtual environment, system dependencies, configuration, and systemd units.

set -euo pipefail

# ANSI color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}    AI Remote PC Control — Installation Wizard      ${NC}"
echo -e "${BLUE}====================================================${NC}"

# 1. Check Python version
echo -e "\n${BLUE}[1/5] Checking Python environment...${NC}"
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}[ERROR] python3 could not be found. Please install Python 3.10+ first.${NC}"
    exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${GREEN}✓ Found Python ${PY_VERSION}${NC}"

# 2. Check & Advise on System Tools
echo -e "\n${BLUE}[2/5] Checking system display utilities...${NC}"
MISSING_TOOLS=()

if [[ -n "${WAYLAND_DISPLAY:-}" ]]; then
    command -v grim &>/dev/null || MISSING_TOOLS+=("grim (Wayland screenshots)")
    command -v slurp &>/dev/null || MISSING_TOOLS+=("slurp (Wayland geometry)")
fi

if [[ -n "${DISPLAY:-}" ]]; then
    command -v xdotool &>/dev/null || MISSING_TOOLS+=("xdotool (X11 GUI input)")
fi

if [ ${#MISSING_TOOLS[@]} -gt 0 ]; then
    echo -e "${YELLOW}[!] Recommended tools for full desktop automation:${NC}"
    for tool in "${MISSING_TOOLS[@]}"; do
        echo -e "    - ${tool}"
    done
    echo -e "${YELLOW}Install them using your package manager (e.g., sudo pacman -S grim slurp xdotool or sudo apt install grim slurp xdotool).${NC}"
else
    echo -e "${GREEN}✓ All desktop display utilities detected.${NC}"
fi

# 3. Create Python Virtual Environment
echo -e "\n${BLUE}[3/5] Setting up Python virtual environment...${NC}"
if [ ! -d "agent/.venv" ]; then
    python3 -m venv agent/.venv
    echo -e "${GREEN}✓ Created virtual environment at agent/.venv${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists at agent/.venv${NC}"
fi

echo -e "Installing core dependencies..."
agent/.venv/bin/pip install --upgrade pip
agent/.venv/bin/pip install -r agent/requirements.txt
agent/.venv/bin/pip install pytest

echo -e "${GREEN}✓ Python packages installed successfully.${NC}"

# 4. Initialize Configuration
echo -e "\n${BLUE}[4/5] Initializing configuration...${NC}"
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${GREEN}✓ Created .env file from .env.example${NC}"
else
    echo -e "${GREEN}✓ .env file already present.${NC}"
fi

# 5. Optional Systemd User Service Setup
echo -e "\n${BLUE}[5/5] Checking systemd service installation...${NC}"
if [[ "${1:-}" == "--systemd" ]] || [[ "${INSTALL_SERVICES:-}" == "true" ]]; then
    SYSTEMD_DIR="${HOME}/.config/systemd/user"
    mkdir -p "$SYSTEMD_DIR"

    # Replace %h placeholder with real home directory if needed
    sed "s|%h/ai-remote-pc-control|${SCRIPT_DIR}|g" deploy/systemd/ai-remote-pc.service > "$SYSTEMD_DIR/ai-remote-pc.service"
    sed "s|%h/ai-remote-pc-control|${SCRIPT_DIR}|g" deploy/systemd/ai-remote-streaming.service > "$SYSTEMD_DIR/ai-remote-streaming.service"

    systemctl --user daemon-reload
    systemctl --user enable ai-remote-pc.service
    systemctl --user enable ai-remote-streaming.service

    echo -e "${GREEN}✓ Systemd user services installed and enabled!${NC}"
    echo -e "To start the services now, run:"
    echo -e "  systemctl --user start ai-remote-pc"
    echo -e "  systemctl --user start ai-remote-streaming"
else
    echo -e "To install systemd background services, run:"
    echo -e "  ./install.sh --systemd"
fi

echo -e "\n${GREEN}====================================================${NC}"
echo -e "${GREEN}   Installation Complete! Ready to Run.            ${NC}"
echo -e "${GREEN}====================================================${NC}"
echo -e "Quick run commands:"
echo -e "  1. Start MCP Server:       agent/.venv/bin/python agent/main.py"
echo -e "  2. Start Streaming Server: agent/.venv/bin/python streaming/server.py"
echo -e "  3. Launch Viewer:          agent/.venv/bin/python viewer/viewer.py"
