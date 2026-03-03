"""
Live integration test for LLM Router with actual Ollama and OpenRouter.

Run manually:
    .venv/bin/python -m pytest tests/integration/test_llm_router_live.py -v -s

Requires:
    - Ollama running on localhost:11434
    - At least qwen2.5:3b model pulled
    - Optionally OPENROUTER_API_KEY in .env for remote tests
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
except ImportError:
    pass


def _ollama_available() -> bool:
    """Check if Ollama is running."""
    try:
        import httpx
        resp = httpx.get("http://localhost:11434/api/tags", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def _has_ollama_model(model: str) -> bool:
    """Check if a specific Ollama model is available."""
    try:
        import httpx
        resp = httpx.get("http://localhost:11434/api/tags", timeout=5)
        if resp.status_code != 200:
            return False
        models = [m["name"] for m in resp.json().get("models", [])]
        return any(model in m for m in models)
    except Exception:
        return False


skip_no_ollama = pytest.mark.skipif(
    not _ollama_available(),
    reason="Ollama not running on localhost:11434",
)

skip_no_openrouter = pytest.mark.skipif(
    not os.environ.get("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set",
)


# ---------------------------------------------------------------------------
# Live Ollama tests
# ---------------------------------------------------------------------------

@skip_no_ollama
class TestLiveOllama:
    """Live tests using local Ollama models."""

    @pytest.mark.asyncio
    async def test_text_completion_ollama(self):
        """Basic text completion via Ollama fallback."""
        from nlp2cmd.llm.router import LLMRouter

        router = LLMRouter()
        resp = await router.completion(
            "What is 2+2? Reply with just the number.",
            task="fast",
            max_tokens=200,
            temperature=0.0,
        )

        print(f"\n  Model: {resp.model}")
        print(f"  Content: {resp.content!r}")
        print(f"  Latency: {resp.latency_ms:.0f}ms")
        print(f"  Tokens: {resp.tokens_used}")

        assert resp.success, f"Failed: {resp.error}"
        # Some models (deepseek-r1) wrap answer in <think> tags
        assert "4" in resp.content or "four" in resp.content.lower()
        assert resp.task == "fast"

    @pytest.mark.asyncio
    async def test_coding_completion_ollama(self):
        """Code generation via Ollama coding model."""
        from nlp2cmd.llm.router import LLMRouter

        router = LLMRouter()
        resp = await router.completion(
            "Write a shell command to list files in /tmp sorted by size. Reply with ONLY the command.",
            task="coding",
            max_tokens=100,
            temperature=0.0,
        )

        print(f"\n  Model: {resp.model}")
        print(f"  Content: {resp.content!r}")
        print(f"  Latency: {resp.latency_ms:.0f}ms")

        assert resp.success, f"Failed: {resp.error}"
        assert resp.task == "coding"
        # Should contain ls or find
        content_lower = resp.content.lower()
        assert "ls" in content_lower or "find" in content_lower or "du" in content_lower

    @pytest.mark.asyncio
    async def test_auto_classification_and_routing(self):
        """Auto-classify prompt and route to correct model."""
        from nlp2cmd.llm.router import LLMRouter

        router = LLMRouter()
        resp = await router.auto_completion(
            "napisz zapytanie SQL dla tabeli users — pokaż 5 najnowszych",
            max_tokens=200,
            temperature=0.0,
        )

        print(f"\n  Auto-task: {resp.task}")
        print(f"  Model: {resp.model}")
        print(f"  Content: {resp.content!r}")
        print(f"  Latency: {resp.latency_ms:.0f}ms")

        assert resp.success, f"Failed: {resp.error}"
        # Should classify as coding (SQL keyword)
        assert resp.task == "coding"

    @pytest.mark.asyncio
    async def test_polish_model(self):
        """Polish language model test."""
        if not _has_ollama_model("bielik"):
            pytest.skip("Bielik model not available")

        from nlp2cmd.llm.router import LLMRouter

        router = LLMRouter()
        resp = await router.completion(
            "Wyjaśnij po polsku czym jest Linux w jednym zdaniu.",
            task="polish",
            max_tokens=200,
            temperature=0.1,
        )

        print(f"\n  Model: {resp.model}")
        print(f"  Content: {resp.content!r}")
        print(f"  Latency: {resp.latency_ms:.0f}ms")

        assert resp.success, f"Failed: {resp.error}"
        assert resp.task == "polish"

    @pytest.mark.asyncio
    async def test_validation_model(self):
        """Validation task (fast, local)."""
        from nlp2cmd.llm.router import LLMRouter

        router = LLMRouter()
        resp = await router.completion(
            'User asked: "list files". Command: "ls -la". Output: "total 128\\ndrwxr-xr-x  5 user user  4096 Mar  1 10:00 .". '
            'Is this a pass or fail? Reply JSON: {"verdict":"pass","score":0.9,"reason":"..."}',
            task="validation",
            max_tokens=200,
            temperature=0.0,
            json_mode=True,
        )

        print(f"\n  Model: {resp.model}")
        print(f"  Content: {resp.content!r}")
        print(f"  Latency: {resp.latency_ms:.0f}ms")

        assert resp.success, f"Failed: {resp.error}"
        assert resp.task == "validation"

    @pytest.mark.asyncio
    async def test_health_and_stats_after_calls(self):
        """Verify stats are recorded after live calls."""
        from nlp2cmd.llm.router import LLMRouter

        router = LLMRouter()

        # Make a call
        await router.completion("Say hello", task="fast", max_tokens=20)

        stats = router.get_stats()
        print(f"\n  Stats: {stats}")

        assert stats["total_calls"] >= 1
        health = router.get_health()
        assert len(health) >= 1

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not _has_ollama_model("qwen2.5vl"),
        reason="qwen2.5vl model not available (still pulling?)",
    )
    async def test_vision_local_qwen_vl(self):
        """Vision test with local Qwen2.5-VL model."""
        import base64
        import struct
        import zlib
        from nlp2cmd.llm.router import LLMRouter

        # Generate a valid 64x64 red PNG
        def _make_png(w: int, h: int, r: int, g: int, b: int) -> bytes:
            raw = b""
            for _ in range(h):
                raw += b"\x00" + bytes([r, g, b]) * w
            compressed = zlib.compress(raw)

            def chunk(ctype: bytes, data: bytes) -> bytes:
                c = ctype + data
                crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
                return struct.pack(">I", len(data)) + c + crc

            sig = b"\x89PNG\r\n\x1a\n"
            ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
            return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")

        png_bytes = _make_png(64, 64, 255, 0, 0)
        b64 = base64.b64encode(png_bytes).decode()

        router = LLMRouter()
        resp = await router.vision(
            b64,
            "What color is this image? Reply with one word.",
            max_tokens=50,
        )

        print(f"\n  Model: {resp.model}")
        print(f"  Content: {resp.content!r}")
        print(f"  Latency: {resp.latency_ms:.0f}ms")

        assert resp.success, f"Failed: {resp.error}"
        assert resp.task == "vision"


# ---------------------------------------------------------------------------
# Live OpenRouter tests
# ---------------------------------------------------------------------------

@skip_no_openrouter
class TestLiveOpenRouter:
    """Live tests using remote OpenRouter models."""

    @pytest.mark.asyncio
    async def test_remote_text_completion(self):
        """Remote text completion via OpenRouter."""
        from nlp2cmd.llm.router import LLMRouter

        router = LLMRouter()
        resp = await router.completion(
            "What is the capital of Poland? Reply with just the city name.",
            task="text",
            max_tokens=50,
            temperature=0.0,
        )

        print(f"\n  Model: {resp.model}")
        print(f"  Content: {resp.content!r}")
        print(f"  Latency: {resp.latency_ms:.0f}ms")
        print(f"  Tokens: {resp.tokens_used}")

        assert resp.success, f"Failed: {resp.error}"
        assert "warszaw" in resp.content.lower() or "warsaw" in resp.content.lower()

    @pytest.mark.asyncio
    async def test_remote_coding_completion(self):
        """Remote coding model via OpenRouter."""
        from nlp2cmd.llm.router import LLMRouter

        router = LLMRouter()
        resp = await router.completion(
            "Write a SELECT SQL query to get 10 most recent orders. Reply with ONLY the SQL.",
            task="coding",
            max_tokens=200,
            temperature=0.0,
        )

        print(f"\n  Model: {resp.model}")
        print(f"  Content: {resp.content!r}")
        print(f"  Latency: {resp.latency_ms:.0f}ms")

        assert resp.success, f"Failed: {resp.error}"
        assert "select" in resp.content.lower()
        assert "order" in resp.content.lower()

    @pytest.mark.asyncio
    async def test_remote_vision(self):
        """Remote vision model via OpenRouter."""
        import base64
        import struct
        import zlib
        from nlp2cmd.llm.router import LLMRouter

        # Generate a valid 64x64 red PNG
        def _make_png(w: int, h: int, r: int, g: int, b: int) -> bytes:
            raw = b""
            for _ in range(h):
                raw += b"\x00" + bytes([r, g, b]) * w
            compressed = zlib.compress(raw)

            def chunk(ctype: bytes, data: bytes) -> bytes:
                c = ctype + data
                crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
                return struct.pack(">I", len(data)) + c + crc

            sig = b"\x89PNG\r\n\x1a\n"
            ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
            return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")

        png_bytes = _make_png(64, 64, 255, 0, 0)
        b64 = base64.b64encode(png_bytes).decode()

        router = LLMRouter()
        resp = await router.vision(
            b64,
            "What color is this image? Reply with one word.",
            max_tokens=50,
        )

        print(f"\n  Model: {resp.model}")
        print(f"  Content: {resp.content!r}")
        print(f"  Latency: {resp.latency_ms:.0f}ms")

        assert resp.success, f"Failed: {resp.error}"
        assert resp.task == "vision"


# ---------------------------------------------------------------------------
# Fallback chain test
# ---------------------------------------------------------------------------

@skip_no_ollama
class TestFallbackChain:
    """Test that routing falls back correctly."""

    @pytest.mark.asyncio
    async def test_fallback_from_unavailable_remote_to_local(self):
        """If no OPENROUTER_API_KEY, should fallback to Ollama."""
        from nlp2cmd.llm.router import LLMRouter

        # Create router with empty API key
        import os
        old_key = os.environ.pop("OPENROUTER_API_KEY", None)
        try:
            router = LLMRouter()
            resp = await router.completion(
                "Say 'hello world'",
                task="text",
                max_tokens=20,
            )

            print(f"\n  Model: {resp.model}")
            print(f"  Content: {resp.content!r}")

            assert resp.success, f"Failed: {resp.error}"
            assert "ollama" in resp.model.lower(), f"Expected Ollama fallback, got: {resp.model}"
        finally:
            if old_key:
                os.environ["OPENROUTER_API_KEY"] = old_key
