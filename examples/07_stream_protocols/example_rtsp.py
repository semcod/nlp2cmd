#!/usr/bin/env python3
"""
Example: RTSP stream — video analysis (color, motion, objects).

Prerequisites:
    pip install opencv-python-headless

Usage:
    python3 examples/07_stream_protocols/example_rtsp.py
    # Or via CLI:
    nlp2cmd --source rtsp://camera:554/stream -q "what colors are dominant?"
    nlp2cmd --source rtsp://192.168.1.50/live -q "is there motion?"
"""

from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from nlp2cmd.streams import StreamRouter, parse_source_uri


def main():
    print("=== RTSP Stream Analysis Examples ===\n")

    # Example 1: Parse RTSP URIs
    uris = [
        "rtsp://camera:554/stream",
        "rtsp://admin:pass@192.168.1.50:554/live",
        "rtsp://cam.local/h264",
    ]
    for raw in uris:
        uri = parse_source_uri(raw)
        print(f"  {raw}")
        print(f"    → host={uri.host}, port={uri.port}, path={uri.path}, is_visual={uri.is_visual}\n")

    # Example 2: Analysis queries
    print("--- Available Analysis Types ---\n")
    queries = [
        ("what colors are dominant?", "Color analysis — HSV histogram of dominant hues"),
        ("is there motion?", "Motion detection — frame differencing between 2 captures"),
        ("what objects are visible?", "Object detection — LLM vision or OpenCV edges"),
        ("count people in frame", "Object counting — requires LLM vision model"),
        ("is it bright or dark?", "Brightness analysis — mean luminance + lighting condition"),
        ("capture frame", "Raw frame capture — returns PNG screenshot"),
    ]
    for q, desc in queries:
        print(f"  \"{q}\"")
        print(f"    → {desc}")
        print(f"    CLI: nlp2cmd --source rtsp://cam:554/stream -q \"{q}\"\n")

    # Example 3: Color analysis output format
    print("--- Color Analysis Output ---")
    print("""
    {
        "colors": {"green": 35.2, "blue": 28.1, "red": 15.4, ...},
        "avg_brightness": 142.5,
        "avg_saturation": 98.3
    }
    """)

    # Example 4: Motion detection output
    print("--- Motion Detection Output ---")
    print("""
    {
        "has_motion": true,
        "motion_percent": 12.4,
        "motion_regions": 3
    }
    """)

    # Example 5: Multi-query workflow
    print("--- Multi-Query Workflow ---")
    print("  # Monitor a security camera:")
    print("  nlp2cmd --source rtsp://cam/stream -q 'is there motion?'")
    print("  nlp2cmd --source rtsp://cam/stream -q 'what colors are dominant?'")
    print("  nlp2cmd --source rtsp://cam/stream -q 'is it bright or dark?'")
    print("  nlp2cmd --source rtsp://cam/stream -q 'capture frame'")

    # Example 6: Integration with other streams
    print("\n--- Integration with SSH + RTSP ---")
    print("  # Check camera status via SSH, then analyze stream:")
    print("  nlp2cmd --source ssh://cam-server -q 'systemctl status motion'")
    print("  nlp2cmd --source rtsp://cam-server:554/stream -q 'what objects are visible?'")


if __name__ == "__main__":
    main()
