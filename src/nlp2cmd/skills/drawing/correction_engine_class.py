# CorrectionEngine - extracted from correction_engine.py
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
from nlp2cmd.skills.drawing.correction_plan import CorrectionPlan
from nlp2cmd.skills.drawing.correction_result import CorrectionResult
from nlp2cmd.skills.drawing.correction_step import CorrectionStep

class CorrectionEngine:
    """
    Iterative correction engine for drawing repair.

    Flow:
    1. Receive ValidationResult with corrections
    2. Build CorrectionPlan from corrections
    3. Execute plan via DrawingSkill
    4. Take screenshot and re-validate
    5. Repeat until correct or max_iterations

    Usage:
        engine = CorrectionEngine(skill, renderer, validator)
        result = await engine.correct(
            validation_result=validation,
            description="red star",
            max_iterations=3,
        )
    """

    def __init__(self, skill: Any, renderer: Any, validator: Optional[VisualValidator] = None):
        """
        Args:
            skill: DrawingSkill instance
            renderer: Renderer instance (PlaywrightRenderer, etc.)
            validator: VisualValidator instance (created if None)
        """
        self._skill = skill
        self._renderer = renderer
        self._validator = validator or VisualValidator()
        self._llm_router = None

    def _get_router(self):
        """Lazy-init LLM router for advanced correction planning."""
        if self._llm_router is None:
            try:
                from nlp2cmd.llm.router import get_router
                self._llm_router = get_router()
            except ImportError:
                pass
        return self._llm_router

    async def correct(self, validation_result: ValidationResult, description: str,
                      screenshot_dir: str = ".", max_iterations: int = 3,
                      verbose: bool = False) -> CorrectionResult:
        """
        Iteratively correct a drawing based on validation feedback.

        Args:
            validation_result: Initial validation with corrections
            description: Original drawing description
            screenshot_dir: Directory for intermediate screenshots
            max_iterations: Maximum correction cycles
            verbose: Print progress

        Returns:
            CorrectionResult with final status
        """
        t0 = time.time()
        history = [validation_result]
        corrections_applied: list[str] = []
        current = validation_result

        if verbose:
            print(f"\n🔧 Correction Engine: {len(current.corrections)} issues to fix")

        for iteration in range(1, max_iterations + 1):
            if not current.needs_correction:
                break

            if verbose:
                print(f"\n  📝 Iteration {iteration}/{max_iterations}")

            # Build correction plan
            plan = await self._build_plan(current, description, verbose)
            if not plan.steps:
                if verbose:
                    print("  ⚠ No actionable corrections, stopping")
                break

            # Execute corrections
            applied = await self._execute_plan(plan, verbose)
            corrections_applied.extend(applied)

            # Take screenshot
            screenshot_path = f"{screenshot_dir}/correction_{iteration}.png"
            await self._renderer.screenshot(screenshot_path)

            # Re-validate
            if verbose:
                print(f"  📸 Re-validating after corrections...")
            current = await self._validator.revalidate(
                screenshot_path=screenshot_path,
                description=description,
                previous_result=current,
                corrections_applied=applied,
                verbose=verbose,
            )
            history.append(current)

            if current.verdict == ValidationVerdict.CORRECT:
                if verbose:
                    print(f"  ✅ Drawing validated as correct!")
                break

        elapsed = (time.time() - t0) * 1000

        return CorrectionResult(
            success=(current.verdict == ValidationVerdict.CORRECT),
            iterations=len(history) - 1,  # exclude initial validation
            final_verdict=current.verdict,
            corrections_applied=corrections_applied,
            total_time_ms=elapsed,
            history=history,
        )

    async def _build_plan(self, validation: ValidationResult, description: str,
                          verbose: bool = False) -> CorrectionPlan:
        """Build a correction plan from validation results."""
        steps: list[CorrectionStep] = []

        for correction in validation.corrections:
            new_steps = self._correction_to_steps(correction, description)
            steps.extend(new_steps)

        # If no rule-based steps, try LLM planning
        if not steps and validation.corrections:
            llm_steps = await self._llm_plan_corrections(validation, description, verbose)
            steps.extend(llm_steps)

        if verbose and steps:
            print(f"  📋 Correction plan: {len(steps)} steps")
            for s in steps[:5]:
                print(f"     • {s.action}: {s.params}")

        return CorrectionPlan(steps=steps, description=f"Fix: {description}")

    def _correction_to_steps(self, correction: DrawingCorrection,
                             description: str) -> list[CorrectionStep]:
        """Convert a single DrawingCorrection to executable steps."""
        steps: list[CorrectionStep] = []

        if correction.action == "redraw":
            # Clear and redraw the target
            if correction.target in ("all", "everything"):
                steps.append(CorrectionStep(action="clear", source_correction=correction))
                steps.append(CorrectionStep(
                    action="draw_from_description",
                    params={"description": description},
                    source_correction=correction,
                ))
            else:
                # Redraw specific shape
                steps.append(CorrectionStep(
                    action="draw_shape",
                    params={
                        "shape_type": correction.target,
                        "color": correction.details.get("color", ""),
                    },
                    source_correction=correction,
                ))

        elif correction.action == "recolor":
            color = correction.details.get("color", correction.details.get("expected_color", ""))
            if color:
                steps.append(CorrectionStep(
                    action="set_color",
                    params={"color": color},
                    source_correction=correction,
                ))
                # Need to redraw with new color
                steps.append(CorrectionStep(
                    action="draw_shape",
                    params={
                        "shape_type": correction.target,
                        "color": color,
                    },
                    source_correction=correction,
                ))

        elif correction.action == "add":
            # Add missing element
            steps.append(CorrectionStep(
                action="draw_shape",
                params={
                    "shape_type": correction.target,
                    "color": correction.details.get("color", "#000000"),
                },
                source_correction=correction,
            ))

        elif correction.action == "resize":
            scale = correction.details.get("scale", 1.5)
            steps.append(CorrectionStep(
                action="clear", source_correction=correction,
            ))
            steps.append(CorrectionStep(
                action="draw_from_description",
                params={"description": description, "size_multiplier": scale},
                source_correction=correction,
            ))

        elif correction.action == "move":
            # Clear and redraw at new position
            steps.append(CorrectionStep(action="clear", source_correction=correction))
            steps.append(CorrectionStep(
                action="draw_from_description",
                params={"description": description},
                source_correction=correction,
            ))

        elif correction.action == "remove":
            # Clear and redraw without the target
            steps.append(CorrectionStep(action="clear", source_correction=correction))
            steps.append(CorrectionStep(
                action="draw_from_description",
                params={"description": description, "exclude": correction.target},
                source_correction=correction,
            ))

        return steps

    async def _llm_plan_corrections(self, validation: ValidationResult,
                                     description: str,
                                     verbose: bool = False) -> list[CorrectionStep]:
        """Use LLM to plan corrections when rule-based mapping fails."""
        router = self._get_router()
        if router is None:
            return []

        issues_text = "\n".join([f"- {c.issue}" for c in validation.corrections])
        prompt = f"""A drawing was supposed to show: "{description}"
The vision model found these issues:
{issues_text}

What drawing commands should fix this? Return JSON:
{{"steps": [{{"action": "clear|draw_shape|set_color", "params": {{"shape_type": "...", "color": "..."}}}}]}}
"""
        try:
            resp = await router.route_call(prompt=prompt, task_category="repair", timeout=15)
            if resp and resp.text:
                import json
                import re
                text = resp.text
                if "```" in text:
                    text = text.split("```")[1].split("```")[0]
                    if text.startswith("json"):
                        text = text[4:]
                start = text.find("{")
                end = text.rfind("}")
                if start >= 0 and end > start:
                    text = text[start:end + 1]
                text = re.sub(r',\s*}', '}', text)
                text = re.sub(r',\s*]', ']', text)
                data = json.loads(text)
                steps = []
                for s in data.get("steps", []):
                    steps.append(CorrectionStep(
                        action=s.get("action", "draw_shape"),
                        params=s.get("params", {}),
                    ))
                if verbose and steps:
                    print(f"  🤖 LLM planned {len(steps)} correction steps")
                return steps
        except Exception as e:
            if verbose:
                print(f"  ⚠ LLM correction planning failed: {e}")

        return []

    async def _execute_plan(self, plan: CorrectionPlan,
                            verbose: bool = False) -> list[str]:
        """Execute a correction plan and return list of applied correction descriptions."""
        applied: list[str] = []

        for step in plan.steps:
            try:
                if step.action == "clear":
                    await self._renderer.clear()
                    applied.append("Cleared canvas")

                elif step.action == "set_color":
                    color = step.params.get("color", "#000000")
                    await self._renderer.set_color(color)
                    applied.append(f"Set color to {color}")

                elif step.action == "draw_shape":
                    shape_type = step.params.get("shape_type", "circle")
                    color = step.params.get("color", "")
                    if color:
                        self._skill.set_color(color)
                    self._skill.draw(shape_type, color=color)
                    # Re-render latest shape
                    shapes = self._skill.get_shapes()
                    if shapes:
                        from nlp2cmd.skills.drawing.events import ShapeDrawn
                        last = shapes[-1]
                        event = ShapeDrawn(
                            shape_type=last["shape_type"],
                            points=last["points"],
                            color=last["color"],
                            fill=last["fill"],
                            center_x=last["center_x"],
                            center_y=last["center_y"],
                        )
                        await self._renderer.draw_shape(event)
                    applied.append(f"Drew {shape_type}")

                elif step.action == "draw_from_description":
                    desc = step.params.get("description", "")
                    if desc:
                        events = self._skill.execute_nl(desc)
                        # Render new shapes
                        for event in events:
                            from nlp2cmd.skills.drawing.events import ShapeDrawn
                            if isinstance(event, ShapeDrawn):
                                await self._renderer.draw_shape(event)
                        applied.append(f"Redrew from description: {desc}")

                if verbose:
                    print(f"     ✓ {step.action}: {step.params}")

            except Exception as e:
                if verbose:
                    print(f"     ✗ {step.action} failed: {e}")
                applied.append(f"FAILED: {step.action} - {e}")

        return applied
