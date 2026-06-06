"""Debug helper functions for pipeline runner."""

from __future__ import annotations

import os
import sys
import time

_DEBUG = os.environ.get("NLP2CMD_DEBUG", "").lower() in ("1", "true", "yes")

__all__ = ["_DEBUG", "_debug", "_with_epipe_retry"]


def _debug(msg: str) -> None:
    """Print debug message to stderr when NLP2CMD_DEBUG=1."""
    if _DEBUG:
        print(f"DEBUG [PipelineRunner] {msg}", file=sys.stderr, flush=True)


def _with_epipe_retry(func, max_retries: int = 3, backoff_ms: int = 500):
    """Execute a Playwright operation with retry logic for EPIPE errors.
    
    EPIPE (broken pipe) errors occur when the Node.js process communication
    breaks. We retry with exponential backoff to allow the connection to recover.
    
    Args:
        func: Callable that performs the Playwright operation
        max_retries: Maximum number of retry attempts
        backoff_ms: Initial backoff in milliseconds (doubles each retry)
    
    Returns:
        The result of func() if successful
    
    Raises:
        The last exception if all retries fail
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            is_epipe = "epipe" in err_str or "broken pipe" in err_str or "econnreset" in err_str
            
            if not is_epipe:
                # Not an EPIPE error, fail immediately
                raise
            
            # EPIPE error - retry with backoff
            wait_ms = min(backoff_ms * (2 ** attempt), 5000)  # Cap at 5 seconds
            _debug(f"EPIPE error on attempt {attempt + 1}/{max_retries}, waiting {wait_ms}ms before retry: {e}")
            time.sleep(wait_ms / 1000)
    
    # All retries exhausted
    raise last_error if last_error else RuntimeError("EPIPE retry failed")
