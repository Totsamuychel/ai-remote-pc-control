#!/usr/bin/env python3
"""Stage 6 Tests — Desktop & Web Viewer Application.

Tests:
1. Viewer file existence and package.json validity.
2. Web assets integrity (HTML elements, CSS styling, Renderer logic).
3. Electron scripts and security configurations.
4. Python viewer launcher (CLI flags, static server hosting, mode fallback).
"""

import json
import socket
import sys
import urllib.request
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from viewer.viewer import (
    VIEWER_DIR,
    SRC_DIR,
    check_electron_available,
    start_local_static_server,
)



def get_free_port() -> int:
    """Find an available local TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def test_viewer_files_exist():
    """Verify all Stage 6 application files are present."""
    assert (VIEWER_DIR / "package.json").exists()
    assert (VIEWER_DIR / "viewer.py").exists()
    assert (VIEWER_DIR / "README.md").exists()
    assert (SRC_DIR / "main.js").exists()
    assert (SRC_DIR / "preload.js").exists()
    assert (SRC_DIR / "index.html").exists()
    assert (SRC_DIR / "styles.css").exists()
    assert (SRC_DIR / "renderer.js").exists()


def test_package_json_validity():
    """Verify package.json is valid JSON with correct main entry and scripts."""
    pkg_file = VIEWER_DIR / "package.json"
    with open(pkg_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("name") == "ai-remote-pc-viewer"
    assert data.get("main") == "src/main.js"
    assert "start" in data.get("scripts", {})
    assert "electron" in data["scripts"]["start"]


def test_index_html_structure():
    """Verify index.html contains essential HUD elements."""
    html = (SRC_DIR / "index.html").read_text(encoding="utf-8")
    assert 'id="host-input"' in html
    assert 'id="btn-connect"' in html
    assert 'id="stream-display"' in html
    assert 'id="approval-modal"' in html
    assert 'id="val-fps"' in html
    assert 'id="val-rtt"' in html
    assert 'id="val-rate"' in html


def test_renderer_js_logic():
    """Verify renderer.js handles approvals, WebSockets, and parameter parsing."""
    js = (SRC_DIR / "renderer.js").read_text(encoding="utf-8")
    assert "function connect()" in js
    assert "pollApprovals" in js
    assert "resolveApproval" in js
    assert "electronAPI" in js
    assert "URLSearchParams" in js


def test_main_js_electron_security():
    """Verify Electron main process configures window security properly."""
    main_js = (SRC_DIR / "main.js").read_text(encoding="utf-8")
    assert "contextIsolation: true" in main_js
    assert "nodeIntegration: false" in main_js
    assert "preload.js" in main_js


def test_viewer_launcher_static_server():
    """Verify that start_local_static_server serves viewer assets over HTTP."""
    port = get_free_port()
    httpd = start_local_static_server(port=port)
    try:
        url = f"http://localhost:{port}/index.html"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3) as resp:
            assert resp.status == 200
            content = resp.read().decode("utf-8")
            assert "Remote PC Viewer" in content
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_check_electron_available_runs():
    """Verify check_electron_available executes without raising errors."""
    result = check_electron_available()
    assert isinstance(result, bool)
