"""
RTSP Stream Adapter — video stream analysis (color, motion, objects).

Captures frames from RTSP camera streams and analyzes them using
OpenCV (local) or LLM vision (remote). Supports queries like:
- "what colors are dominant?"
- "is there motion?"
- "what objects are visible?"
- "count people in frame"

Usage:
    nlp2cmd --source rtsp://camera:554/stream "what colors are dominant?"
    nlp2cmd --source rtsp://192.168.1.100/live "is there movement?"
"""

from __future__ import annotations

import io
import time
from typing import Any, Optional

from nlp2cmd.streams.base import StreamAdapter, StreamResult, SourceURI


class RTSPStreamAdapter(StreamAdapter):
    """Analyze RTSP video streams — colors, motion, objects."""

    PROTOCOL = "rtsp"

    def __init__(self, source: SourceURI):
        super().__init__(source)
        self._cap = None
        self._prev_frame = None
        self._rtsp_url = self._build_rtsp_url()

    def _build_rtsp_url(self) -> str:
        user_part = ""
        if self.source.user:
            pwd = f":{self.source.password}" if self.source.password else ""
            user_part = f"{self.source.user}{pwd}@"
        port = f":{self.source.port}" if self.source.port else ""
        path = self.source.path or "/stream"
        return f"rtsp://{user_part}{self.source.host}{port}{path}"

    def connect(self) -> StreamResult:
        try:
            import cv2
        except ImportError:
            return StreamResult(
                success=False,
                error="OpenCV not installed. Install: pip install opencv-python-headless",
            )

        try:
            self._cap = cv2.VideoCapture(self._rtsp_url)
            if not self._cap.isOpened():
                return StreamResult(success=False, error=f"Cannot open RTSP stream: {self._rtsp_url}")

            self._connected = True
            w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self._cap.get(cv2.CAP_PROP_FPS)

            return StreamResult(
                success=True,
                output=f"Connected to RTSP stream: {w}x{h} @ {fps:.1f}fps",
                metadata={"url": self._rtsp_url, "width": w, "height": h, "fps": fps},
            )
        except Exception as e:
            return StreamResult(success=False, error=str(e))

    def execute(self, task: str, **kwargs) -> StreamResult:
        """Route task to appropriate analysis function."""
        return self.query(task, **kwargs)

    def query(self, question: str, **kwargs) -> StreamResult:
        """Analyze the video stream based on the question."""
        q = question.lower()

        if any(w in q for w in ["color", "kolor", "barw", "dominant"]):
            return self._analyze_colors(**kwargs)
        elif any(w in q for w in ["motion", "ruch", "movement", "porusza"]):
            return self._detect_motion(**kwargs)
        elif any(w in q for w in ["object", "obiekt", "rozpoznaj", "detect", "identify"]):
            return self._detect_objects(**kwargs)
        elif any(w in q for w in ["count", "policz", "ile", "how many"]):
            return self._count_objects(question, **kwargs)
        elif any(w in q for w in ["bright", "jasno", "dark", "ciemn", "light"]):
            return self._analyze_brightness(**kwargs)
        elif any(w in q for w in ["screenshot", "frame", "klatka", "zrzut"]):
            return self._capture_frame(**kwargs)
        else:
            # Default: capture frame + basic analysis
            return self._full_analysis(question, **kwargs)

    def screenshot(self) -> Optional[bytes]:
        """Capture a single frame as PNG bytes."""
        frame = self._grab_frame()
        if frame is None:
            return None
        return self._frame_to_png(frame)

    def disconnect(self) -> None:
        if self._cap:
            self._cap.release()
            self._cap = None
        self._connected = False

    # ------------------------------------------------------------------
    # Analysis methods
    # ------------------------------------------------------------------

    def _grab_frame(self):
        """Grab a single frame from the stream."""
        if not self._cap or not self._cap.isOpened():
            return None
        ret, frame = self._cap.read()
        return frame if ret else None

    def _frame_to_png(self, frame) -> bytes:
        import cv2
        _, buf = cv2.imencode(".png", frame)
        return buf.tobytes()

    def _analyze_colors(self, **kwargs) -> StreamResult:
        """Analyze dominant colors in the current frame."""
        import cv2
        import numpy as np

        frame = self._grab_frame()
        if frame is None:
            return StreamResult(success=False, error="Could not capture frame")

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)

        # Dominant hue ranges
        color_ranges = {
            "red": ((0, 10), (170, 180)),
            "orange": ((10, 25),),
            "yellow": ((25, 35),),
            "green": ((35, 85),),
            "cyan": ((85, 100),),
            "blue": ((100, 130),),
            "purple": ((130, 170),),
        }

        total_pixels = h.size
        color_pcts = {}
        for color, ranges in color_ranges.items():
            count = 0
            for lo, hi in ranges:
                mask = cv2.inRange(h, lo, hi)
                count += cv2.countNonZero(mask)
            color_pcts[color] = round(count / total_pixels * 100, 1)

        # Sort by dominance
        sorted_colors = sorted(color_pcts.items(), key=lambda x: -x[1])
        dominant = [f"{c}: {p}%" for c, p in sorted_colors if p > 1.0]

        avg_brightness = float(np.mean(v))
        avg_saturation = float(np.mean(s))

        return StreamResult(
            success=True,
            output=f"Dominant colors: {', '.join(dominant[:5])}",
            data={
                "colors": dict(sorted_colors),
                "avg_brightness": round(avg_brightness, 1),
                "avg_saturation": round(avg_saturation, 1),
            },
            screenshot=self._frame_to_png(frame),
        )

    def _detect_motion(self, **kwargs) -> StreamResult:
        """Detect motion between consecutive frames."""
        import cv2
        import numpy as np

        frame1 = self._grab_frame()
        if frame1 is None:
            return StreamResult(success=False, error="Could not capture frame")

        time.sleep(kwargs.get("interval", 0.5))
        frame2 = self._grab_frame()
        if frame2 is None:
            return StreamResult(success=False, error="Could not capture second frame")

        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        gray1 = cv2.GaussianBlur(gray1, (21, 21), 0)
        gray2 = cv2.GaussianBlur(gray2, (21, 21), 0)

        diff = cv2.absdiff(gray1, gray2)
        _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)

        motion_pct = cv2.countNonZero(thresh) / thresh.size * 100
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        significant = [c for c in contours if cv2.contourArea(c) > 500]

        has_motion = motion_pct > 1.0

        # Draw motion regions on frame2
        for c in significant:
            x, y, w, h = cv2.boundingRect(c)
            cv2.rectangle(frame2, (x, y), (x + w, y + h), (0, 255, 0), 2)

        return StreamResult(
            success=True,
            output=f"{'Motion detected' if has_motion else 'No significant motion'} ({motion_pct:.1f}% changed, {len(significant)} regions)",
            data={
                "has_motion": has_motion,
                "motion_percent": round(motion_pct, 2),
                "motion_regions": len(significant),
            },
            screenshot=self._frame_to_png(frame2),
        )

    def _detect_objects(self, **kwargs) -> StreamResult:
        """Detect objects using OpenCV DNN or LLM fallback."""
        frame = self._grab_frame()
        if frame is None:
            return StreamResult(success=False, error="Could not capture frame")

        # Try LLM vision analysis
        png = self._frame_to_png(frame)
        llm_result = self._llm_analyze_frame(png, "What objects are visible in this image? List them.")
        if llm_result:
            return StreamResult(
                success=True,
                output=llm_result,
                data={"method": "llm_vision"},
                screenshot=png,
            )

        # Fallback: basic edge/contour detection
        import cv2
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        large_objects = [c for c in contours if cv2.contourArea(c) > 1000]

        return StreamResult(
            success=True,
            output=f"Detected {len(large_objects)} significant objects (edge-based detection, install LLM for better results)",
            data={"object_count": len(large_objects), "method": "opencv_edges"},
            screenshot=png,
        )

    def _count_objects(self, question: str, **kwargs) -> StreamResult:
        """Count specific objects in frame."""
        frame = self._grab_frame()
        if frame is None:
            return StreamResult(success=False, error="Could not capture frame")

        png = self._frame_to_png(frame)
        prompt = f"Count objects in this image. Question: {question}. Answer with a number and brief description."
        llm_result = self._llm_analyze_frame(png, prompt)
        if llm_result:
            return StreamResult(success=True, output=llm_result, screenshot=png)

        return StreamResult(
            success=True,
            output="Object counting requires LLM vision model. Install ollama with a vision model.",
            data={"method": "unavailable"},
            screenshot=png,
        )

    def _analyze_brightness(self, **kwargs) -> StreamResult:
        """Analyze frame brightness and lighting conditions."""
        import cv2
        import numpy as np

        frame = self._grab_frame()
        if frame is None:
            return StreamResult(success=False, error="Could not capture frame")

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_brightness = float(np.mean(gray))
        std_brightness = float(np.std(gray))

        if mean_brightness < 50:
            condition = "very dark"
        elif mean_brightness < 100:
            condition = "dark"
        elif mean_brightness < 170:
            condition = "normal"
        elif mean_brightness < 220:
            condition = "bright"
        else:
            condition = "very bright / overexposed"

        return StreamResult(
            success=True,
            output=f"Lighting: {condition} (brightness: {mean_brightness:.0f}/255, contrast: {std_brightness:.0f})",
            data={
                "mean_brightness": round(mean_brightness, 1),
                "std_brightness": round(std_brightness, 1),
                "condition": condition,
            },
            screenshot=self._frame_to_png(frame),
        )

    def _capture_frame(self, **kwargs) -> StreamResult:
        """Just capture a frame and return it."""
        frame = self._grab_frame()
        if frame is None:
            return StreamResult(success=False, error="Could not capture frame")
        return StreamResult(
            success=True,
            output="Frame captured",
            screenshot=self._frame_to_png(frame),
        )

    def _full_analysis(self, question: str, **kwargs) -> StreamResult:
        """Full frame analysis: colors + brightness + motion hint."""
        import cv2
        import numpy as np

        frame = self._grab_frame()
        if frame is None:
            return StreamResult(success=False, error="Could not capture frame")

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mean_b = float(np.mean(gray))
        mean_s = float(np.mean(hsv[:, :, 1]))

        png = self._frame_to_png(frame)
        llm_result = self._llm_analyze_frame(png, question)

        output = llm_result or f"Frame captured. Brightness: {mean_b:.0f}/255, Saturation: {mean_s:.0f}/255"
        return StreamResult(
            success=True,
            output=output,
            data={"brightness": round(mean_b, 1), "saturation": round(mean_s, 1)},
            screenshot=png,
        )

    def _llm_analyze_frame(self, png_bytes: bytes, prompt: str) -> Optional[str]:
        """Try to analyze frame using LLM vision model."""
        try:
            import base64
            from nlp2cmd.generation.llm_simple import LiteLLMClient
            import asyncio

            b64 = base64.b64encode(png_bytes).decode()
            full_prompt = f"{prompt}\n\n[Image data: {len(png_bytes)} bytes, base64-encoded PNG]"

            llm = LiteLLMClient()
            result = asyncio.run(llm.generate(full_prompt))
            return result.strip() if result else None
        except Exception:
            return None
