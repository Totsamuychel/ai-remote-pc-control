#!/usr/bin/env python3
"""AI Remote PC Desktop Viewer Launcher.

Provides flexible launch targets for connecting to the remote streaming feed:
1. Native Electron Desktop App (if node/npm/electron installed)
2. Default Web Browser (connecting to remote streaming server or local web viewer)
3. Terminal Viewer (ANSI TrueColor or Kitty Graphics protocol)
"""

import argparse
import http.server
import os
import shutil
import socketserver
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

VIEWER_DIR = Path(__file__).parent.resolve()
SRC_DIR = VIEWER_DIR / "src"
PROJECT_ROOT = VIEWER_DIR.parent.resolve()

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def check_electron_available() -> bool:
    """Check if Electron or npm/npx is available to run the desktop viewer."""
    if shutil.which("electron"):
        return True
    if shutil.which("npx"):
        return True
    if shutil.which("npm") and (VIEWER_DIR / "node_modules" / "electron").exists():
        return True
    return False


def launch_electron(host: str) -> bool:
    """Launch the Electron desktop viewer application."""
    print(f"[*] Launching Electron Desktop Viewer connected to {host}...")
    
    # Priority 1: Direct electron command
    if shutil.which("electron"):
        cmd = ["electron", str(SRC_DIR / "main.js"), f"--host={host}"]
        try:
            return subprocess.call(cmd, cwd=str(VIEWER_DIR)) == 0
        except Exception as e:
            print(f"[!] Error executing electron directly: {e}")

    # Priority 2: npm start
    if shutil.which("npm"):
        env = os.environ.copy()
        env["REMOTE_HOST"] = host
        cmd = ["npm", "start", "--prefix", str(VIEWER_DIR)]
        try:
            return subprocess.call(cmd, env=env) == 0
        except Exception as e:
            print(f"[!] Error running npm start: {e}")

    # Priority 3: npx electron
    if shutil.which("npx"):
        cmd = ["npx", "electron", str(SRC_DIR / "main.js"), f"--host={host}"]
        try:
            return subprocess.call(cmd, cwd=str(VIEWER_DIR)) == 0
        except Exception as e:
            print(f"[!] Error running npx electron: {e}")

    return False


def start_local_static_server(port: int = 3000) -> socketserver.TCPServer:
    """Start a lightweight background HTTP server serving viewer/src files."""
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(SRC_DIR), **kwargs)

        def log_message(self, format, *args):
            # Suppress normal access logs to keep terminal clean
            pass

    httpd = socketserver.TCPServer(("", port), Handler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    return httpd


def launch_browser(host: str, serve_local: bool = False, port: int = 3000) -> bool:
    """Open the viewer interface in the system default web browser."""
    clean_host = host.replace("http://", "").replace("https://", "").rstrip("/")

    if serve_local:
        print(f"[*] Starting local viewer server on http://localhost:{port}...")
        start_local_static_server(port)
        url = f"http://localhost:{port}/?host={clean_host}"
    else:
        # Connect directly to the FastAPI streaming server
        url = f"http://{clean_host}/"

    print(f"[*] Opening browser viewer at: {url}")
    return webbrowser.open(url)


def launch_terminal(fps: int = 15, max_cols: int = 80) -> int:
    """Launch the terminal stream viewer directly."""
    from streaming.terminal_viewer import run_terminal_stream
    return run_terminal_stream(fps=fps, max_cols=max_cols)


def main():
    parser = argparse.ArgumentParser(
        description="AI Remote PC - Desktop & Browser Viewer Launcher"
    )
    parser.add_argument(
        "--host",
        default="localhost:8080",
        help="Streaming server host:port (e.g., localhost:8080 or Tailscale IP 100.x.y.z:8080)",
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "electron", "browser", "terminal"],
        default="auto",
        help="Viewer target: auto (try Electron then browser), electron, browser, terminal",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=15,
        help="Target streaming frame rate (for terminal viewer)",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Host viewer HTML/JS locally on a lightweight static server",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=3000,
        help="Port for local static server (if --serve is enabled)",
    )

    args = parser.parse_args()

    if args.mode == "terminal":
        print(f"[*] Starting Terminal Viewer at {args.fps} FPS...")
        return launch_terminal(fps=args.fps)

    if args.mode == "electron":
        if not check_electron_available():
            print("[!] Electron runtime or npm/npx not detected.")
            print("[!] Falling back to browser...")
            launch_browser(args.host, serve_local=args.serve, port=args.port)
            return 0
        success = launch_electron(args.host)
        return 0 if success else 1

    if args.mode == "browser":
        launch_browser(args.host, serve_local=args.serve, port=args.port)
        return 0

    # Auto mode: try Electron, fallback to browser
    if check_electron_available():
        try:
            print("[*] Electron environment detected. Starting desktop app...")
            if launch_electron(args.host):
                return 0
        except Exception as e:
            print(f"[!] Electron launch failed ({e}), falling back to browser.")

    print("[*] Launching browser viewer...")
    launch_browser(args.host, serve_local=args.serve, port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
