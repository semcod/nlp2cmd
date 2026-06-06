# AutonomousDrawingPipeline - extracted from correction_engine.py
"""
Correction Engine — iterative drawing repair based on visual validation feedback.

After VisualValidator identifies issues, this engine:
1. Interprets correction instructions
2. Maps corrections to drawing commands (clear, redraw, recolor, move)
3. Executes corrections via DrawingSkill + Renderer
4. Re-validates until correct or max iterations reached

Pipeline:
    ValidationResult.corrections → CorrectionPlan → execute → re-screenshot → re-validate

Single Responsibility: correction instructions → drawing command sequence → execution.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from nlp2cmd.skills.drawing.visual_validator import (
    DrawingCorrection,
    ValidationResult,
    ValidationVerdict,
    VisualValidator,
)
from nlp2cmd.skills.drawing.correction_engine_class import CorrectionEngine

class AutonomousDrawingPipeline:
    """
    Full autonomous drawing pipeline: draw → validate → correct → repeat.

    Combines DrawingSkill, Renderer, ObjectFetcher, TextToShapeEngine,
    VisualValidator, and CorrectionEngine into a single autonomous workflow.

    Usage:
        pipeline = AutonomousDrawingPipeline(skill, renderer)
        result = await pipeline.draw_and_validate(
            "red star with blue background",
            max_corrections=3,
        )
    """

    def __init__(self, skill: Any, renderer: Any,
                 validator: Optional[VisualValidator] = None,
                 correction_engine: Optional[CorrectionEngine] = None):
        self._skill = skill
        self._renderer = renderer
        self._validator = validator or VisualValidator()
        self._correction = correction_engine or CorrectionEngine(
            skill, renderer, self._validator
        )

    def _print_header(self, description: str) -> None:
        """Print pipeline header."""
        print("🎨 Autonomous Drawing Pipeline")
        print(f"   Description: {description}")
        print()

    async def _initial_drawing(self, description: str, verbose: bool) -> tuple[Any, dict[str, Any]]:
        """Perform initial drawing from description.
        
        Returns:
            Tuple of (events, canvas_info)
        """
        if verbose:
            print("  📝 Step 1: Drawing from description...")

        events = self._skill.execute_nl(description)
        canvas_info = await self._skill.render(self._renderer)

        if verbose:
            n_shapes = sum(1 for e in events if hasattr(e, 'shape_type'))
            print(f"     Drew {n_shapes} shapes on {canvas_info.get('width', '?')}x{canvas_info.get('height', '?')} canvas")

        return events, canvas_info

    async def _take_screenshot(self, screenshot_dir: str) -> str:
        """Take screenshot and return path."""
        initial_screenshot = f"{screenshot_dir}/initial_drawing.png"
        await self._renderer.screenshot(initial_screenshot)
        return initial_screenshot

    async def _validate_drawing(self, screenshot_path: str, description: str, verbose: bool) -> ValidationResult:
        """Validate drawing against description."""
        if verbose:
            print("\n  🔍 Step 2: Visual validation...")

        return await self._validator.validate(
            screenshot_path=screenshot_path,
            description=description,
            verbose=verbose,
        )

    async def _apply_corrections(self, validation: ValidationResult, description: str,
                                 screenshot_dir: str, max_corrections: int, verbose: bool) -> Any:
        """Apply corrections if needed."""
        if not validation.needs_correction or max_corrections <= 0:
            return None

        if verbose:
            print(f"\n  🔧 Step 3: Applying corrections ({len(validation.corrections)} issues)...")

        return await self._correction.correct(
            validation_result=validation,
            description=description,
            screenshot_dir=screenshot_dir,
            max_iterations=max_corrections,
            verbose=verbose,
        )

    def _get_final_verdict(self, correction_result: Any, validation: ValidationResult) -> ValidationVerdict:
        """Determine final verdict from correction result or initial validation."""
        return (
            correction_result.final_verdict if correction_result
            else validation.verdict
        )

    def _build_result(self, description: str, final_verdict: ValidationVerdict,
                     validation: ValidationResult, correction_result: Any,
                     elapsed: float, initial_screenshot: str) -> dict[str, Any]:
        """Build result dictionary."""
        return {
            "description": description,
            "verdict": final_verdict.value,
            "success": final_verdict == ValidationVerdict.CORRECT,
            "initial_validation": {
                "verdict": validation.verdict.value,
                "confidence": validation.confidence,
                "what_model_sees": validation.description,
                "issues": len(validation.corrections),
            },
            "corrections": {
                "applied": correction_result.corrections_applied if correction_result else [],
                "iterations": correction_result.iterations if correction_result else 0,
            },
            "total_time_ms": elapsed,
            "screenshots": {
                "initial": initial_screenshot,
            },
        }

    def _print_summary(self, final_verdict: ValidationVerdict, elapsed: float) -> None:
        """Print execution summary."""
        icons = {"correct": "✅", "partial": "⚠️", "wrong": "❌", "empty": "🔲", "error": "💥"}
        icon = icons.get(final_verdict.value, "?")
        print(f"\n  {icon} Final verdict: {final_verdict.value}")
        print(f"     Total time: {elapsed:.0f}ms")

    async def draw_and_validate(self, description: str,
                                screenshot_dir: str = ".",
                                max_corrections: int = 3,
                                verbose: bool = False) -> dict[str, Any]:
        """
        Autonomous drawing with validation and correction loop.

        Args:
            description: What to draw (natural language, PL or EN)
            screenshot_dir: Directory for screenshots
            max_corrections: Max correction iterations
            verbose: Print detailed progress

        Returns:
            Dict with results: verdict, iterations, screenshots, etc.
        """
        t0 = time.time()

        if verbose:
            self._print_header(description)

        # Step 1: Initial drawing
        await self._initial_drawing(description, verbose)

        # Step 2: Screenshot
        initial_screenshot = await self._take_screenshot(screenshot_dir)

        # Step 3: Validate
        validation = await self._validate_drawing(initial_screenshot, description, verbose)

        # Step 4: Correct if needed
        correction_result = await self._apply_corrections(
            validation, description, screenshot_dir, max_corrections, verbose
        )

        elapsed = (time.time() - t0) * 1000
        final_verdict = self._get_final_verdict(correction_result, validation)
        result = self._build_result(description, final_verdict, validation, correction_result, elapsed, initial_screenshot)

        if verbose:
            self._print_summary(final_verdict, elapsed)

        return result
