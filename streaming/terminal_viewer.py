#!/usr/bin/env python3
"""Terminal Screen Viewer for AI Remote PC Control.

Enables live desktop streaming directly inside the terminal using:
1. High-Resolution Kitty Graphics Protocol (for Kitty terminal).
2. Universal 24-bit TrueColor ANSI Unicode Half-Blocks (▀) for all modern terminals.
"""

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.tools.screen import capture_screenshot


def detect_terminal_capability() -> str:
    """Detect whether terminal supports native Kitty graphics or universal ANSI."""
    if os.environ.get("KITTY_WINDOW_ID") or os.environ.get("TERM") == "xterm-kitty":
        if shutil.which("kitten"):
            return "kitty"
    return "ansi"


def render_ansi_halfblock(image_path: str, max_cols: int = 80) -> str:
    """Render an image using 24-bit TrueColor ANSI escape codes and Unicode half-blocks (▀).

    Each character cell represents two vertical pixels:
    - Foreground color = Top pixel
    - Background color = Bottom pixel
    """
    try:
        from PIL import Image

        with Image.open(image_path) as img:
            img = img.convert("RGB")
            w, h = img.size
            aspect = h / w

            # Terminal characters are roughly twice as tall as they are wide
            cols = max_cols
            rows = max(1, int(cols * aspect * 0.5))

            # Resize image to match terminal pixel matrix
            resized = img.resize((cols, rows * 2), Image.Resampling.BILINEAR)
            pixels = resized.load()

            lines = []
            for y in range(0, rows * 2, 2):
                line_parts = []
                for x in range(cols):
                    tr, tg, tb = pixels[x, y]
                    br, bg, bb = pixels[x, y + 1] if y + 1 < rows * 2 else (0, 0, 0)
                    line_parts.append(f"\033[38;2;{tr};{tg};{tb}m\033[48;2;{br};{bg};{bb}m▀")
                line_parts.append("\033[0m")
                lines.append("".join(line_parts))

            return "\n".join(lines)
    except Exception as e:
        return f"[Render Error] Failed to render image in ANSI: {e}"


def display_frame(image_path: str, mode: str = "auto", max_cols: int = 80):
    """Display an image frame in the terminal using the specified mode."""
    selected_mode = detect_terminal_capability() if mode == "auto" else mode

    if selected_mode == "kitty" and shutil.which("kitten"):
        # Use high-resolution Kitty Graphics Protocol
        try:
            subprocess.run(["kitten", "icat", "--align", "left", "--clear"], check=False)
            subprocess.run(["kitten", "icat", "--align", "left", image_path], check=True)
            return
        except Exception:
            # Fallback to ANSI on failure
            pass

    # Universal ANSI TrueColor rendering
    ascii_art = render_ansi_halfblock(image_path, max_cols=max_cols)
    print(ascii_art)


def run_live_terminal_stream(fps: int = 10, mode: str = "auto", max_cols: int = 80):
    """Run a real-time live terminal streaming loop."""
    interval = 1.0 / max(1, fps)
    print(f"\033[2J\033[H", end="")  # Clear terminal
    print(f"=== Starting Live Terminal Screen Stream (target {fps} FPS, mode: {mode}) ===")
    print("Press Ctrl+C to stop.\n")

    frame_count = 0
    start_time = time.time()
    last_fps_update = time.time()
    measured_fps = 0.0

    temp_frame_path = "/tmp/remote_pc_terminal_frame.jpg"

    try:
        while True:
            t0 = time.time()

            # Capture frame
            shot = capture_screenshot(output_path=temp_frame_path, quality=70, format="jpeg")
            if not shot.get("success"):
                print(f"[Capture Error] {shot.get('error')}")
                time.sleep(1.0)
                continue

            frame_count += 1
            now = time.time()
            if now - last_fps_update >= 1.0:
                measured_fps = frame_count / (now - last_fps_update)
                frame_count = 0
                last_fps_update = now

            # Reset cursor to top-left of terminal
            print(f"\033[H", end="")
            header = (
                f"\033[1;37;44m [LIVE REMOTE PC STREAM] \033[0m "
                f"FPS: \033[1;32m{measured_fps:.1f}\033[0m | "
                f"Res: {shot.get('width')}x{shot.get('height')} | "
                f"Size: {round(shot.get('size_bytes', 0) / 1024, 1)} KB | "
                f"Mode: {mode.upper()} "
                f"\033[K"
            )
            print(header)

            display_frame(temp_frame_path, mode=mode, max_cols=max_cols)

            elapsed = time.time() - t0
            sleep_time = max(0.01, interval - elapsed)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n\n=== Terminal stream stopped by user ===")
    finally:
        if os.path.exists(temp_frame_path):
            try:
                os.remove(temp_frame_path)
            except OSError:
                pass


def main():
    parser = argparse.ArgumentParser(description="Live Terminal Desktop Viewer for AI Remote PC Control")
    parser.add_argument("--mode", choices=["auto", "kitty", "ansi"], default="auto", help="Rendering engine")
    parser.add_argument("--fps", type=int, default=8, help="Target frames per second for live stream")
    parser.add_argument("--cols", type=int, default=100, help="Terminal columns for ANSI mode")
    parser.add_argument("--once", action="store_true", help="Capture and display a single frame then exit")
    args = parser.parse_args()

    if args.once:
        temp_path = "/tmp/remote_pc_terminal_snapshot.jpg"
        shot = capture_screenshot(output_path=temp_path, quality=85)
        if shot.get("success"):
            print(f"\n[Snapshot] {shot.get('width')}x{shot.get('height')}, {round(shot.get('size_bytes',0)/1024,1)} KB:")
            display_frame(temp_path, mode=args.mode, max_cols=args.cols)
            if os.path.exists(temp_path):
                os.remove(temp_path)
        else:
            print(f"[Error] {shot.get('error')}")
    else:
        run_live_terminal_stream(fps=args.fps, mode=args.mode, max_cols=args.cols)


if __name__ == "__main__":
    main()
