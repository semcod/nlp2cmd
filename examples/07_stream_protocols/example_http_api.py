#!/usr/bin/env python3
"""
Example: HTTP stream — interact with REST APIs.

Usage:
    python3 examples/07_stream_protocols/example_http_api.py
    # Or via CLI:
    nlp2cmd --source http://jsonplaceholder.typicode.com -q "get /posts"
"""

from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from nlp2cmd.streams import StreamRouter, parse_source_uri


def main():
    router = StreamRouter()

    print("=== HTTP API Stream Examples ===\n")

    # Example 1: GET request to public API
    print("--- GET Requests ---")
    print("  nlp2cmd --source http://jsonplaceholder.typicode.com -q 'get /posts'")
    print("  nlp2cmd --source https://api.github.com -q 'get /users/wronai'")
    print("  nlp2cmd --source http://localhost:8080/api/v1 -q 'get /health'")

    # Example 2: POST/PUT/DELETE
    print("\n--- Mutation Requests ---")
    print("  nlp2cmd --source http://api.example.com --run -q 'create /users'")
    print("  nlp2cmd --source http://api.example.com --run -q 'update /users/1'")
    print("  nlp2cmd --source http://api.example.com --run -q 'delete /posts/42'")

    # Example 3: Live demo with jsonplaceholder
    print("\n--- Live Demo (jsonplaceholder.typicode.com) ---")
    result = router.execute("https://jsonplaceholder.typicode.com", "get /todos/1")
    print(f"  Result: success={result.success}")
    if result.output:
        print(f"  Output: {result.output[:300]}")
    if result.data:
        print(f"  Data keys: {list(result.data.keys())[:10]}")

    # Example 4: WebSocket
    print("\n--- WebSocket Examples ---")
    print("  nlp2cmd --source ws://echo.websocket.org --run -q 'send hello world'")
    print("  nlp2cmd --source wss://stream.binance.com/ws --run -q 'subscribe btcusdt'")
    print("  nlp2cmd --source ws://localhost:8080/live -q 'receive'")


if __name__ == "__main__":
    main()
