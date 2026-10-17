"""High-performance desktop screen capture engine for real-time video streaming.

Captures frames via native Wayland tools (grim) or cross-platform mss, compresses
to in-memory JPEG bytes, and provides telemetry statistics (FPS, latency, frame size).
"""

import io
import os
import platform
import shutil
import subprocess
import threading
import time
from typing import Any, Dict, Optional, Tuple

try:
    import mss
    from PIL import Image
except ImportError:
    mss = None
    Image = None


class ScreenCapture:
    """Manages high-speed frame capture and JPEG encoding."""

    def __init__(self, default_quality: int = 70, scale: float = 1.0):
        self.default_quality = default_quality
        self.scale = scale
        self.is_wayland = bool(os.environ.get("WAYLAND_DISPLAY") and shutil.which("grim"))
        self._sct = None
        self._sct_monitor = None
        self._lock = threading.Lock()

        # Cached frame for multi-client concurrency optimization
        self._cached_frame: Optional[bytes] = None
        self._cached_dim: Tuple[int, int] = (0, 0)
        self._cached_time: float = 0.0

        self._init_mss()

        # Telemetry
        self.last_capture_time = 0.0
        self.frame_count = 0
        self.fps = 0.0
        self._fps_window_start = time.time()
        self.resolution: Tuple[int, int] = (0, 0)


    def _init_mss(self):
        """Initialize mss screen grabber if not using native Wayland grim."""
        if not self.is_wayland and mss:
            try:
                sct_cls = getattr(mss, "MSS", getattr(mss, "mss", None))
                self._sct = sct_cls()
                # Monitor 0 = all monitors combined, Monitor 1 = primary display
                if len(self._sct.monitors) > 1:
                    self._sct_monitor = self._sct.monitors[1]
                else:
                    self._sct_monitor = self._sct.monitors[0]
                self.resolution = (self._sct_monitor["width"], self._sct_monitor["height"])
            except Exception:
                self._sct = None

    def capture_jpeg(
        self,
        quality: Optional[int] = None,
        scale: Optional[float] = None,
    ) -> Tuple[Optional[bytes], int, int]:
        """Capture one desktop frame and return encoded JPEG bytes and dimensions.

        Args:
            quality: JPEG quality level (1-100).
            scale: Downscale factor (e.g. 0.75 or 0.5) to reduce bandwidth.

        Returns:
            Tuple of (jpeg_bytes, width, height) or (None, 0, 0) on failure.
        """
        q = quality or self.default_quality
        s = scale or self.scale

        with self._lock:
            now = time.time()
            # Reuse cached frame if captured within the last 25ms (e.g. 40 FPS threshold)
            if self._cached_frame and (now - self._cached_time) < 0.025:
                return self._cached_frame, self._cached_dim[0], self._cached_dim[1]

            jpeg_data = None
            width, height = 0, 0

            # Method 1: Wayland grim capture (returns native compositor frame)
            if self.is_wayland:
                try:
                    proc = subprocess.run(["grim", "-t", "jpeg", "-q", str(q), "-"], capture_output=True, timeout=1.5)
                    if proc.returncode == 0 and proc.stdout:
                        raw_bytes = proc.stdout
                        if s < 1.0 and Image:
                            with Image.open(io.BytesIO(raw_bytes)) as img:
                                orig_w, orig_h = img.size
                                new_size = (int(orig_w * s), int(orig_h * s))
                                resized = img.resize(new_size, Image.Resampling.BILINEAR)
                                buf = io.BytesIO()
                                resized.save(buf, format="JPEG", quality=q)
                                jpeg_data = buf.getvalue()
                                width, height = new_size
                        else:
                            jpeg_data = raw_bytes
                            if Image:
                                with Image.open(io.BytesIO(jpeg_data)) as img:
                                    width, height = img.size
                except Exception:
                    jpeg_data = None

            # Method 2: Fallback to mss + Pillow
            if jpeg_data is None and mss and Image:
                if self._sct is None:
                    self._init_mss()

                if self._sct and self._sct_monitor:
                    try:
                        shot = self._sct.grab(self._sct_monitor)
                        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
                        orig_w, orig_h = shot.width, shot.height

                        if s < 1.0:
                            new_w, new_h = int(orig_w * s), int(orig_h * s)
                            img = img.resize((new_w, new_h), Image.Resampling.BILINEAR)
                            width, height = new_w, new_h
                        else:
                            width, height = orig_w, orig_h

                        buf = io.BytesIO()
                        img.save(buf, format="JPEG", quality=q)
                        jpeg_data = buf.getvalue()
                    except Exception:
                        jpeg_data = None

            if jpeg_data:
                self.resolution = (width, height)
                self.frame_count += 1
                dt = now - self._fps_window_start
                if dt >= 1.0:
                    self.fps = round(self.frame_count / dt, 1)
                    self.frame_count = 0
                    self._fps_window_start = now
                self.last_capture_time = now
                self._cached_frame = jpeg_data
                self._cached_dim = (width, height)
                self._cached_time = now

            return jpeg_data, width, height


    def get_stats(self) -> Dict[str, Any]:
        """Return current performance telemetry."""
        return {
            "fps": self.fps,
            "resolution": f"{self.resolution[0]}x{self.resolution[1]}",
            "is_wayland": self.is_wayland,
            "engine": "grim (Wayland)" if self.is_wayland else "mss (X11/Win)",
        }

    def close(self):
        """Release underlying capture resources."""
        if self._sct:
            try:
                self._sct.close()
            except Exception:
                pass
            self._sct = None
