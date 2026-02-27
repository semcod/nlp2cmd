"""Tests for desktop automation — Wayland detection, ydotool keymaps, fallback logic."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from nlp2cmd.automation.action_planner import (
    ActionPlanner,
    _can_use_desktop_automation,
)
from nlp2cmd.pipeline_runner import PipelineRunner


# ── Wayland detection ───────────────────────────────────────────────────

class TestCanUseDesktopAutomation:
    @patch.dict("os.environ", {"XDG_SESSION_TYPE": "x11", "WAYLAND_DISPLAY": ""})
    @patch("shutil.which", side_effect=lambda t: "/usr/bin/xdotool" if t == "xdotool" else None)
    def test_x11_with_xdotool(self, mock_which):
        assert _can_use_desktop_automation() is True

    @patch.dict("os.environ", {"XDG_SESSION_TYPE": "x11", "WAYLAND_DISPLAY": ""})
    @patch("shutil.which", return_value=None)
    def test_x11_without_tools(self, mock_which):
        assert _can_use_desktop_automation() is False

    @patch.dict("os.environ", {"XDG_SESSION_TYPE": "wayland", "WAYLAND_DISPLAY": "wayland-0"})
    @patch("shutil.which", return_value=None)
    def test_wayland_without_ydotool(self, mock_which):
        assert _can_use_desktop_automation() is False

    @patch.dict("os.environ", {"XDG_SESSION_TYPE": "wayland", "WAYLAND_DISPLAY": "wayland-0"})
    @patch("shutil.which", side_effect=lambda t: "/usr/bin/ydotool" if t == "ydotool" else None)
    def test_wayland_with_ydotool(self, mock_which):
        assert _can_use_desktop_automation() is True

    @patch.dict("os.environ", {"XDG_SESSION_TYPE": "", "WAYLAND_DISPLAY": "wayland-0"})
    @patch("shutil.which", return_value=None)
    def test_wayland_detected_by_display_var(self, mock_which):
        assert _can_use_desktop_automation() is False


# ── ydotool key conversion ──────────────────────────────────────────────

class TestXdotoolKeysToYdotool:
    def test_ctrl_t(self):
        result = PipelineRunner._xdotool_keys_to_ydotool("ctrl+t")
        assert result == ["29:1", "20:1", "20:0", "29:0"]

    def test_return(self):
        result = PipelineRunner._xdotool_keys_to_ydotool("Return")
        assert result == ["28:1", "28:0"]

    def test_ctrl_shift_n(self):
        result = PipelineRunner._xdotool_keys_to_ydotool("ctrl+shift+n")
        assert "29:1" in result  # ctrl press
        assert "42:1" in result  # shift press
        assert "49:1" in result  # n press

    def test_escape(self):
        result = PipelineRunner._xdotool_keys_to_ydotool("Escape")
        assert result == ["1:1", "1:0"]

    def test_f5(self):
        result = PipelineRunner._xdotool_keys_to_ydotool("F5")
        assert result == ["63:1", "63:0"]

    def test_alt_tab(self):
        result = PipelineRunner._xdotool_keys_to_ydotool("alt+Tab")
        assert "56:1" in result  # alt press
        assert "15:1" in result  # tab press


# ── Backend detection ───────────────────────────────────────────────────

class TestDetectDesktopBackend:
    @patch.dict("os.environ", {"XDG_SESSION_TYPE": "wayland", "WAYLAND_DISPLAY": "wayland-0"})
    @patch("shutil.which", side_effect=lambda t: "/usr/bin/ydotool" if t == "ydotool" else None)
    def test_wayland_ydotool(self, mock_which):
        assert PipelineRunner._detect_desktop_backend() == "ydotool"

    @patch.dict("os.environ", {"XDG_SESSION_TYPE": "x11", "WAYLAND_DISPLAY": ""})
    @patch("shutil.which", side_effect=lambda t: "/usr/bin/xdotool" if t == "xdotool" else None)
    def test_x11_xdotool(self, mock_which):
        assert PipelineRunner._detect_desktop_backend() == "xdotool"

    @patch.dict("os.environ", {"XDG_SESSION_TYPE": "x11", "WAYLAND_DISPLAY": ""})
    @patch("shutil.which", side_effect=lambda t: "/usr/bin/wmctrl" if t == "wmctrl" else None)
    def test_x11_wmctrl_fallback(self, mock_which):
        assert PipelineRunner._detect_desktop_backend() == "wmctrl"

    @patch.dict("os.environ", {"XDG_SESSION_TYPE": "wayland", "WAYLAND_DISPLAY": "wayland-0"})
    @patch("shutil.which", return_value=None)
    def test_no_tools(self, mock_which):
        assert PipelineRunner._detect_desktop_backend() == "none"


# ── Wayland fallback in action planner ──────────────────────────────────

class TestActionPlannerWaylandFallback:
    @patch("nlp2cmd.automation.action_planner._can_use_desktop_automation", return_value=False)
    def test_firefox_query_falls_back_to_playwright(self, mock_desktop):
        planner = ActionPlanner()
        plan = planner.decompose_sync(
            "otwórz tab w już otwartym oknie przeglądarki firefox "
            "wyciągnij klucz API z OpenRouter i zapisz do .env"
        )
        desktop_steps = [s for s in plan.steps if s.action.startswith("desktop_")]
        assert len(desktop_steps) == 0, "Desktop steps should not be generated on Wayland"
        actions = [s.action for s in plan.steps]
        assert "navigate" in actions
        assert "save_env" in actions

    @patch("nlp2cmd.automation.action_planner._can_use_desktop_automation", return_value=True)
    def test_firefox_query_uses_desktop_on_x11(self, mock_desktop):
        planner = ActionPlanner()
        plan = planner.decompose_sync(
            "otwórz tab w już otwartym oknie przeglądarki firefox "
            "wyciągnij klucz API z OpenRouter i zapisz do .env"
        )
        desktop_steps = [s for s in plan.steps if s.action.startswith("desktop_")]
        assert len(desktop_steps) > 0, "Desktop steps should be generated on X11"

    def test_non_firefox_query_never_uses_desktop(self):
        planner = ActionPlanner()
        plan = planner.decompose_sync(
            "wyciągnij klucz API z OpenRouter i zapisz do .env"
        )
        desktop_steps = [s for s in plan.steps if s.action.startswith("desktop_")]
        assert len(desktop_steps) == 0
