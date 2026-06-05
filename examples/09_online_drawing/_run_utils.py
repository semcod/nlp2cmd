"""
Shared utilities for 09_online_drawing examples.

Provides:
- Structured file logging (JSON + human-readable)
- Intelligent URL discovery with health checks
- Platform-independent browser automation helpers
- Cookie/popup/GDPR banner dismissal
- Retry logic with exponential backoff
- Canvas detection with multiple strategies
"""

from __future__ import annotations

import json
import logging
import os
import platform
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# ── Logging setup ─────────────────────────────────────────────────────────

class ExampleLogger:
    """Structured logger that writes to both file and console."""

    def __init__(self, name: str, log_dir: str | Path = "logs"):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"{name}_{ts}.log"
        self.json_log_file = self.log_dir / f"{name}_{ts}.json"

        self._entries: list[dict[str, Any]] = []
        self._start_time = time.monotonic()

        # Python logger → file + console
        self.logger = logging.getLogger(f"nlp2cmd.example.{name}")
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()

        fh = logging.FileHandler(str(self.log_file), encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)-7s] %(message)s",
            datefmt="%H:%M:%S",
        ))
        self.logger.addHandler(fh)

        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter("%(message)s"))
        self.logger.addHandler(ch)

    def info(self, msg: str, **extra: Any) -> None:
        self.logger.info(msg)
        self._record("INFO", msg, extra)

    def debug(self, msg: str, **extra: Any) -> None:
        self.logger.debug(msg)
        self._record("DEBUG", msg, extra)

    def warning(self, msg: str, **extra: Any) -> None:
        self.logger.warning(f"⚠ {msg}")
        self._record("WARNING", msg, extra)

    def error(self, msg: str, **extra: Any) -> None:
        self.logger.error(f"✗ {msg}")
        self._record("ERROR", msg, extra)

    def success(self, msg: str, **extra: Any) -> None:
        self.logger.info(f"✓ {msg}")
        self._record("SUCCESS", msg, extra)

    def step(self, n: int, msg: str, **extra: Any) -> None:
        self.logger.info(f"{n}. {msg}")
        self._record("STEP", f"[{n}] {msg}", extra)

    def _record(self, level: str, msg: str, extra: dict) -> None:
        entry = {
            "time": datetime.now(timezone.utc).isoformat(),
            "elapsed_s": round(time.monotonic() - self._start_time, 3),
            "level": level,
            "message": msg,
        }
        if extra:
            entry["extra"] = extra
        self._entries.append(entry)

    def save(self) -> Path:
        """Save structured JSON log and return its path."""
        report = {
            "example": self.name,
            "platform": get_platform_info(),
            "started": self._entries[0]["time"] if self._entries else "",
            "duration_s": round(time.monotonic() - self._start_time, 3),
            "entries": self._entries,
            "summary": {
                "total": len(self._entries),
                "errors": sum(1 for e in self._entries if e["level"] == "ERROR"),
                "warnings": sum(1 for e in self._entries if e["level"] == "WARNING"),
                "successes": sum(1 for e in self._entries if e["level"] == "SUCCESS"),
            },
        }
        self.json_log_file.write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        self.logger.info(f"Logs saved: {self.log_file}")
        self.logger.info(f"JSON log:   {self.json_log_file}")
        return self.json_log_file


# ── Platform detection ────────────────────────────────────────────────────

def get_platform_info() -> dict[str, str]:
    """Get platform info for logging and diagnostics."""
    return {
        "os": platform.system(),
        "os_version": platform.version(),
        "arch": platform.machine(),
        "python": platform.python_version(),
        "hostname": platform.node(),
    }


# ── Browser automation helpers ────────────────────────────────────────────

COMMON_POPUPS = [
    # GDPR / Cookie banners
    "Accept", "Accept all", "Akceptuję", "Zaakceptuj wszystko",
    "Accept cookies", "Agree", "Zgadzam się",
    "I understand", "Rozumiem",
    # Generic dismiss
    "OK", "Got it", "Close", "Zamknij", "×", "Zrozumiałem",
    "Skip", "Pomiń", "No thanks", "Nie, dziękuję",
    "Continue", "Kontynuuj", "Dalej",
    # Login prompts
    "Maybe later", "Not now", "Później", "Nie teraz",
]

COOKIE_SELECTORS = [
    '[class*="cookie"] button',
    '[class*="consent"] button',
    '[id*="cookie"] button',
    '[id*="consent"] button',
    '[class*="gdpr"] button',
    '[id*="gdpr"] button',
    '.cc-dismiss', '.cc-allow',
    '#onetrust-accept-btn-handler',
    '[data-testid*="cookie"]',
    '[data-testid*="accept"]',
]

MODAL_CLOSE_SELECTORS = [
    # Modern modal close buttons (SVG icons, aria labels)
    'button[aria-label="Close"]',
    'button[aria-label="close"]',
    'button[aria-label="Zamknij"]',
    '[class*="modal"] button[class*="close"]',
    '[class*="modal"] [class*="close"]',
    '[class*="dialog"] button[class*="close"]',
    '[role="dialog"] button',
    '[class*="overlay"] button[class*="close"]',
    '[class*="popup"] button[class*="close"]',
    'button[class*="dismiss"]',
    # Generic X/close SVG buttons
    'button > svg[class*="close"]',
    '[data-testid="close-button"]',
    '[data-testid="modal-close"]',
]


async def _click_if_visible(page, locator, log: ExampleLogger | None, label: str,
                            timeout: int, pause_ms: int = 300) -> bool:
    try:
        if await locator.count() > 0 and await locator.is_visible():
            await locator.click(timeout=timeout)
            await page.wait_for_timeout(pause_ms)
            if log:
                log.debug(label)
            return True
    except Exception:
        pass
    return False


async def _dismiss_text_popups(page, log: ExampleLogger | None, timeout: int) -> int:
    dismissed = 0
    for text in COMMON_POPUPS:
        if await _click_if_visible(
            page, page.get_by_text(text, exact=False).first, log,
            f"Dismissed popup: '{text}'", timeout,
        ):
            dismissed += 1
    return dismissed


async def _dismiss_selector_popups(page, selectors: list[str], log: ExampleLogger | None,
                                   timeout: int, label_prefix: str, pause_ms: int = 300) -> int:
    dismissed = 0
    for sel in selectors:
        if await _click_if_visible(
            page, page.locator(sel).first, log,
            f"{label_prefix}: {sel}", timeout, pause_ms=pause_ms,
        ):
            dismissed += 1
    return dismissed


async def dismiss_popups(page, log: ExampleLogger | None = None, timeout: int = 3000) -> int:
    """
    Dismiss common popups, cookie banners, GDPR notices.
    Returns count of dismissed elements.
    """
    dismissed = await _dismiss_text_popups(page, log, timeout)
    dismissed += await _dismiss_selector_popups(
        page, COOKIE_SELECTORS, log, timeout, "Dismissed cookie banner",
    )
    dismissed += await _dismiss_selector_popups(
        page, MODAL_CLOSE_SELECTORS, log, timeout, "Dismissed modal", pause_ms=500,
    )

    try:
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(300)
    except Exception:
        pass

    return dismissed


def _classify_page_title(title_lower: str) -> str | None:
    if any(x in title_lower for x in ["404", "not found", "nie znaleziono", "error"]):
        return "error_404"
    if any(x in title_lower for x in ["blocked", "access denied", "forbidden", "zablokowano"]):
        return "blocked"
    if any(x in title_lower for x in ["log in", "sign in", "zaloguj", "login"]):
        return "login_required"
    return None


async def _inspect_required_element(page, required_selector: str, report: dict[str, Any],
                                    log: ExampleLogger | None) -> None:
    try:
        count = await page.locator(required_selector).count()
        report["canvas_count"] = count
        report["has_canvas"] = count > 0
        if count == 0:
            return

        first = page.locator(required_selector).first
        box = await first.bounding_box()
        report["canvas_visible"] = box is not None and box["width"] > 50 and box["height"] > 50
        if box:
            report["canvas_size"] = f"{box['width']:.0f}x{box['height']:.0f}"
    except Exception as e:
        if log:
            log.debug(f"Canvas check error: {e}")


# ── Intelligent URL discovery ─────────────────────────────────────────────

# Known drawing sites with alternative URLs and health check selectors
DRAWING_SITES = {
    "draw.chat": {
        "urls": [
            "https://draw.chat/",
            "https://draw.chat/pl/index.html",
            "https://draw.chat/pl/whiteboard.html",
            "https://draw.chat/en/index.html",
            "https://draw.chat/pl/",
            "https://draw.chat/en/",
        ],
        "canvas_selector": "canvas",
        "health_text": None,
        "description": "Free online whiteboard — no login",
    },
    "jspaint": {
        "urls": [
            "https://jspaint.app",
            "https://jspaint.app/",
            "https://jspaint.app/#local",
        ],
        "canvas_selector": "canvas",
        "health_text": None,
        "description": "MS Paint clone in browser",
    },
    "picsart": {
        "urls": [
            "https://picsart.com/pl/draw",
            "https://picsart.com/draw",
            "https://picsart.com/en/draw",
            "https://picsart.com/create/editor",
        ],
        "canvas_selector": "canvas",
        "health_text": None,
        "description": "Picsart Draw — brushes, layers, colors",
    },
    "excalidraw": {
        "urls": [
            "https://excalidraw.com/",
            "https://excalidraw.com",
        ],
        "canvas_selector": "canvas",
        "health_text": None,
        "description": "Excalidraw — hand-drawn style diagrams",
    },
    "kleki": {
        "urls": [
            "https://kleki.com/",
            "https://kleki.com",
        ],
        "canvas_selector": "canvas",
        "health_text": None,
        "description": "Kleki — online paint tool",
    },
}


async def check_page_health(page, required_selector: str = "canvas",
                             log: ExampleLogger | None = None) -> dict[str, Any]:
    """
    Comprehensive page health check after navigation.
    Returns health report dict.
    """
    report: dict[str, Any] = {
        "url": page.url,
        "title": "",
        "status": "unknown",
        "has_canvas": False,
        "canvas_count": 0,
        "canvas_visible": False,
        "has_errors": False,
        "popups_dismissed": 0,
        "is_404": False,
        "is_blocked": False,
        "is_login_required": False,
    }

    try:
        report["title"] = await page.title()
    except Exception:
        pass

    page_status = _classify_page_title(report["title"].lower())
    if page_status == "error_404":
        report["is_404"] = True
        report["status"] = page_status
        if log:
            log.warning(f"Page returned 404: {page.url}")
        return report
    if page_status == "blocked":
        report["is_blocked"] = True
        report["status"] = page_status
        if log:
            log.warning(f"Page access blocked: {page.url}")
        return report
    if page_status == "login_required":
        report["is_login_required"] = True
        report["status"] = page_status
        if log:
            log.warning(f"Login required: {page.url}")
        return report

    report["popups_dismissed"] = await dismiss_popups(page, log)
    await _inspect_required_element(page, required_selector, report, log)

    # Check for JS errors on page
    try:
        errors = await page.evaluate("""() => {
            return window.__nlp2cmd_errors || [];
        }""")
        if errors:
            report["has_errors"] = True
            report["js_errors"] = errors[:5]
    except Exception:
        pass

    report["status"] = "healthy" if report["canvas_visible"] else (
        "has_canvas" if report["has_canvas"] else "no_canvas"
    )

    return report


def _collect_discovery_urls(custom_urls: list[str] | None, site_urls: list[str]) -> list[str]:
    urls_to_try: list[str] = []
    if custom_urls:
        urls_to_try.extend(custom_urls)
    for url in site_urls:
        if url not in urls_to_try:
            urls_to_try.append(url)

    seen: set[str] = set()
    unique_urls: list[str] = []
    for url in urls_to_try:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)
    return unique_urls


async def _try_discovery_url(
    page,
    url: str,
    required_selector: str,
    timeout_per_url: int,
    log: ExampleLogger | None,
) -> tuple[str | None, dict[str, Any]]:
    response = await page.goto(url, wait_until="domcontentloaded", timeout=timeout_per_url)
    status = response.status if response else 0
    if log:
        log.debug(f"    HTTP {status}")

    if status in (404, 410, 500, 502, 503):
        if log:
            log.debug(f"    → HTTP error {status}, skipping")
        return None, {"url": url, "status": f"http_{status}"}

    await page.wait_for_timeout(3000)
    report = await check_page_health(page, required_selector, log)
    if report["status"] == "healthy":
        if log:
            log.success(f"Found working URL: {page.url} (canvas: {report.get('canvas_size', '?')})")
        return page.url, report

    if report["status"] in ("no_canvas", "has_canvas"):
        canvas_found = await wait_for_canvas(page, required_selector, timeout_s=10, log=log)
        if canvas_found:
            report2 = await check_page_health(page, required_selector, log)
            if report2["status"] == "healthy":
                if log:
                    log.success(f"Found working URL (after canvas wait): {page.url}")
                return page.url, report2
            return None, report2

    if log:
        log.debug(f"    → Status: {report['status']}, trying next")
    return None, report


async def discover_working_url(
    page,
    site_name: str,
    custom_urls: list[str] | None = None,
    required_selector: str = "canvas",
    timeout_per_url: int = 15000,
    log: ExampleLogger | None = None,
) -> tuple[str | None, dict[str, Any]]:
    """
    Intelligent URL discovery with fallback chain and health checks.

    Args:
        page: Playwright page
        site_name: Key in DRAWING_SITES or custom name
        custom_urls: Additional URLs to try
        required_selector: CSS selector that must exist
        timeout_per_url: Timeout per URL attempt
        log: Logger instance

    Returns:
        (working_url, health_report) or (None, last_report)
    """
    site_info = DRAWING_SITES.get(site_name, {})
    if site_info and not required_selector:
        required_selector = site_info.get("canvas_selector", "canvas")

    urls_to_try = _collect_discovery_urls(custom_urls, site_info.get("urls", []))

    if not urls_to_try:
        if log:
            log.error(f"No URLs to try for site '{site_name}'")
        return None, {"status": "no_urls"}

    if log:
        log.info(f"URL discovery: trying {len(urls_to_try)} URLs for '{site_name}'")

    last_report: dict[str, Any] = {}

    for i, url in enumerate(urls_to_try, 1):
        if log:
            log.debug(f"  [{i}/{len(urls_to_try)}] Trying: {url}")
        try:
            working_url, last_report = await _try_discovery_url(
                page, url, required_selector, timeout_per_url, log,
            )
            if working_url:
                return working_url, last_report
        except Exception as e:
            err_msg = str(e)[:100]
            if log:
                log.debug(f"    → Error: {err_msg}")
            last_report = {"url": url, "status": "error", "error": err_msg}

    if log:
        log.error(f"No working URL found for '{site_name}' after {len(urls_to_try)} attempts")

    return None, last_report


# ── Canvas wait helper ─────────────────────────────────────────────────────

async def wait_for_canvas(page, selector: str = "canvas", timeout_s: int = 10,
                           log: ExampleLogger | None = None) -> bool:
    """
    Poll for a visible canvas element up to timeout_s seconds.
    Returns True if a visible canvas was found.
    """
    import asyncio
    deadline = time.monotonic() + timeout_s
    attempt = 0
    while time.monotonic() < deadline:
        attempt += 1
        try:
            count = await page.locator(selector).count()
            if count > 0:
                first = page.locator(selector).first
                box = await first.bounding_box()
                if box and box["width"] > 50 and box["height"] > 50:
                    if log:
                        log.debug(f"Canvas appeared after {attempt} poll(s): {box['width']:.0f}x{box['height']:.0f}")
                    return True
        except Exception:
            pass
        await asyncio.sleep(1)

    if log:
        log.debug(f"Canvas not found after {timeout_s}s polling")
    return False


# ── Retry decorator ───────────────────────────────────────────────────────

async def retry_async(coro_fn, max_retries: int = 3, backoff: float = 1.0,
                       log: ExampleLogger | None = None, label: str = "operation"):
    """Retry an async operation with exponential backoff."""
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            return await coro_fn()
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                wait = backoff * (2 ** (attempt - 1))
                if log:
                    log.warning(f"{label} failed (attempt {attempt}/{max_retries}): {e}, retrying in {wait:.1f}s")
                import asyncio
                await asyncio.sleep(wait)
            else:
                if log:
                    log.error(f"{label} failed after {max_retries} attempts: {e}")
    raise last_error  # type: ignore


# ── Canvas detection strategies ───────────────────────────────────────────

async def find_canvas(page, log: ExampleLogger | None = None) -> dict[str, Any] | None:
    """
    Find the best canvas element using multiple strategies.
    Returns bounding_box dict or None.
    """
    strategies = [
        ("canvas:visible", "canvas"),
        ("canvas[id]", 'canvas[id]'),
        ("canvas.main", 'canvas[class*="main"], canvas[class*="draw"], canvas[class*="paint"]'),
        ("first visible canvas", "canvas"),
        ("svg", "svg"),
    ]

    for name, selector in strategies:
        try:
            elements = page.locator(selector)
            count = await elements.count()
            if count == 0:
                continue

            # Find the largest visible canvas
            best_box = None
            best_area = 0

            for idx in range(min(count, 5)):
                el = elements.nth(idx)
                try:
                    box = await el.bounding_box()
                    if box and box["width"] > 50 and box["height"] > 50:
                        area = box["width"] * box["height"]
                        if area > best_area:
                            best_area = area
                            best_box = box
                except Exception:
                    continue

            if best_box:
                if log:
                    log.debug(f"Canvas found via '{name}': {best_box['width']:.0f}x{best_box['height']:.0f}")
                return best_box

        except Exception:
            continue

    if log:
        log.warning("No suitable canvas found on page")
    return None


# ── Screenshot with metadata ─────────────────────────────────────────────

async def take_screenshot(page, path: str | Path, log: ExampleLogger | None = None,
                           metadata: dict[str, Any] | None = None) -> str | None:
    """Take a screenshot and save metadata alongside it."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    try:
        await page.screenshot(path=str(p))
        if log:
            log.success(f"Screenshot saved: {p}")

        # Save metadata
        if metadata:
            meta_path = p.with_suffix(".meta.json")
            meta = {
                "screenshot": str(p),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "url": page.url,
                "title": await page.title(),
                "platform": get_platform_info(),
                **metadata,
            }
            meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

        return str(p)
    except Exception as e:
        if log:
            log.error(f"Screenshot failed: {e}")
        return None


# ── Run context manager ──────────────────────────────────────────────────

class ExampleRunner:
    """
    Context manager for running drawing examples with full instrumentation.

    Usage:
        async with ExampleRunner("01_draw_chat", headless=True) as runner:
            page = runner.page
            log = runner.log
            ...
    """

    def __init__(self, name: str, headless: bool = False,
                 viewport: dict[str, int] | None = None,
                 base_dir: str | Path | None = None):
        self.name = name
        self.headless = headless
        self.viewport = viewport or {"width": 1280, "height": 900}
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent / name

        self.log_dir = self.base_dir / "logs"
        self.screenshot_dir = self.base_dir / "screenshots"

        self.log = ExampleLogger(name, self.log_dir)
        self.page = None
        self._browser = None
        self._pw = None
        self._pw_ctx = None

    async def __aenter__(self):
        self.log.info(f"=== {self.name} ===")
        self.log.info(f"Platform: {json.dumps(get_platform_info())}")
        self.log.info(f"Headless: {self.headless}")

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            self.log.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
            raise SystemExit(1)

        self._pw_ctx = async_playwright()
        self._pw = await self._pw_ctx.__aenter__()

        try:
            self._browser = await self._pw.chromium.launch(headless=self.headless)
        except Exception as e:
            self.log.error(f"Browser launch failed: {e}")
            self.log.info("Trying to install Chromium...")
            import subprocess
            result = subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                self.log.error(f"Chromium install failed: {result.stderr}")
                raise SystemExit(1)
            self._browser = await self._pw.chromium.launch(headless=self.headless)

        self.page = await self._browser.new_page(viewport=self.viewport)
        self.log.success("Browser ready")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.log.error(f"Exception: {exc_type.__name__}: {exc_val}")
            self.log.debug(traceback.format_exc())

            # Emergency screenshot
            if self.page:
                try:
                    err_path = self.screenshot_dir / "error_screenshot.png"
                    await take_screenshot(self.page, err_path, self.log, metadata={"error": str(exc_val)})
                except Exception:
                    pass

        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass

        if self._pw_ctx:
            try:
                await self._pw_ctx.__aexit__(None, None, None)
            except Exception:
                pass

        self.log.save()
        return False  # Don't suppress exceptions

    async def navigate(self, site_name: str, custom_urls: list[str] | None = None,
                        required_selector: str = "canvas") -> str | None:
        """Navigate to a drawing site with intelligent fallback."""
        url, health = await discover_working_url(
            self.page, site_name,
            custom_urls=custom_urls,
            required_selector=required_selector,
            log=self.log,
        )
        if url:
            self.log.info(f"Navigated to: {url}")
            if health.get("popups_dismissed", 0) > 0:
                self.log.info(f"Dismissed {health['popups_dismissed']} popup(s)")
        else:
            self.log.error(f"Could not navigate to '{site_name}': {health.get('status', 'unknown')}")
        return url

    async def screenshot(self, filename: str, **metadata: Any) -> str | None:
        """Take a screenshot in the example's screenshot directory."""
        path = self.screenshot_dir / filename
        return await take_screenshot(self.page, path, self.log, metadata=metadata)
