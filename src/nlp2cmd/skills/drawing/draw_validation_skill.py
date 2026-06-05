# DrawValidationSkill - extracted from validation.py
"""
DrawValidationSkill — Task-aware vision validation for drawing operations.

Goes beyond simple "does it match?" validation to provide:
1. Task tracking: what was requested, what's done, what remains
2. Per-object status: drawn/missing/wrong/partial
3. Overall scene assessment with Qwen VL
4. Actionable next-step suggestions

Pipeline:
    screenshot → vision_analyze → compare_to_plan → status_report

Single Responsibility: Know what's been drawn and what still needs doing.
"""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from nlp2cmd.skills.drawing.object_assessment import ObjectAssessment
from nlp2cmd.skills.drawing.object_status import ObjectStatus
from nlp2cmd.skills.drawing.task_plan import TaskPlan
from nlp2cmd.skills.drawing.validation_report import ValidationReport

class DrawValidationSkill:
    """
    Task-aware drawing validation using Qwen VL.

    Tracks a drawing plan (what objects to draw) and validates
    the current canvas state against it, reporting:
    - What's done (drawn correctly)
    - What remains (not yet drawn)
    - What's wrong (drawn but incorrect)
    - What to do next (actionable suggestions)

    Usage:
        validator = DrawValidationSkill()

        # Set what we want to draw
        plan = TaskPlan(description="red star and blue house")
        plan.add("star", "#FF0000")
        plan.add("house", "#0000FF")

        # Validate current state
        report = await validator.validate(page, plan)
        print(report.summary())      # "1/2 done (50%), 1 remaining, 0 need fixing"
        print(report.next_actions())  # ["draw house in #0000FF"]

        # After drawing more, check progress
        report2 = await validator.check_progress(page, plan, previous=report)
    """

    def __init__(self, use_vision: bool = True, max_retries: int = 2):
        self._router = None
        self._use_vision = use_vision
        self._max_retries = max_retries

    def _get_router(self):
        if self._router is None:
            from nlp2cmd.skills.drawing.llm_helpers import get_drawing_router
            self._router = get_drawing_router()
        return self._router

    # ── Main validation ───────────────────────────────────────────────

    async def validate(
        self,
        page_or_screenshot,
        plan: TaskPlan,
        verbose: bool = False,
    ) -> ValidationReport:
        """
        Validate current canvas state against the drawing plan.

        Args:
            page_or_screenshot: Playwright page or path to screenshot PNG
            plan: TaskPlan describing what should be drawn
            verbose: Print progress

        Returns:
            ValidationReport with per-object status
        """
        t0 = time.time()
        report = ValidationReport(plan=plan)

        # Get screenshot
        b64, screenshot_path = await self._get_screenshot(page_or_screenshot)
        report.screenshot_path = screenshot_path

        if b64 is None:
            # No screenshot available — mark all as pending
            for obj in plan.objects:
                report.assessments.append(ObjectAssessment(
                    name=obj["name"],
                    requested_color=obj.get("color", ""),
                    status=ObjectStatus.PENDING,
                ))
            report.validation_time_ms = (time.time() - t0) * 1000
            return report

        # Build prompt
        object_list = "\n".join(
            f"- {obj['name']}" + (f" (color: {obj.get('color', 'any')})" if obj.get('color') else "")
            for obj in plan.objects
        )
        prompt = TASK_VALIDATION_PROMPT.format(
            description=plan.description,
            object_list=object_list,
        )

        # Call vision model
        data = await self._vision_call(b64, prompt)

        if data is None:
            # Vision unavailable — use heuristic
            return self._heuristic_validate(plan, screenshot_path, t0)

        # Parse response
        report.scene_description = data.get("scene_description", "")
        report.overall_match = data.get("overall_match", 0.0)
        report.model_used = "vision"

        for obj_data in data.get("objects", []):
            name = obj_data.get("name", "unknown")
            status_str = obj_data.get("status", "missing").lower()
            status_map = {
                "drawn": ObjectStatus.DRAWN,
                "missing": ObjectStatus.MISSING,
                "wrong": ObjectStatus.WRONG,
                "partial": ObjectStatus.PARTIAL,
            }

            # Find matching plan object for color info
            plan_color = ""
            for po in plan.objects:
                if po["name"].lower() == name.lower():
                    plan_color = po.get("color", "")
                    break

            report.assessments.append(ObjectAssessment(
                name=name,
                status=status_map.get(status_str, ObjectStatus.MISSING),
                requested_color=plan_color,
                actual_color=obj_data.get("actual_color", ""),
                issue=obj_data.get("issue", ""),
                suggestion=obj_data.get("suggestion", ""),
                confidence=obj_data.get("confidence", 0.5),
            ))

        # Ensure all plan objects have an assessment
        assessed_names = {a.name.lower() for a in report.assessments}
        for obj in plan.objects:
            if obj["name"].lower() not in assessed_names:
                report.assessments.append(ObjectAssessment(
                    name=obj["name"],
                    status=ObjectStatus.MISSING,
                    requested_color=obj.get("color", ""),
                    issue="Not mentioned in vision analysis",
                ))

        report.validation_time_ms = (time.time() - t0) * 1000

        if verbose:
            self._print_report(report)

        return report

    # ── Progress check (incremental) ──────────────────────────────────

    async def check_progress(
        self,
        page_or_screenshot,
        plan: TaskPlan,
        previous: ValidationReport,
        verbose: bool = False,
    ) -> ValidationReport:
        """
        Incremental progress check — compare against previous validation.

        More efficient than full validate() because it focuses on
        what was remaining last time.
        """
        t0 = time.time()

        b64, screenshot_path = await self._get_screenshot(page_or_screenshot)
        if b64 is None:
            return previous

        completed = [a.name for a in previous.done]
        remaining = [a.name for a in previous.remaining]

        prompt = PROGRESS_CHECK_PROMPT.format(
            description=plan.description,
            completed_list=", ".join(completed) if completed else "none",
            remaining_list=", ".join(remaining) if remaining else "none",
        )

        data = await self._vision_call(b64, prompt)
        if data is None:
            return previous

        # Update assessments based on progress
        report = ValidationReport(plan=plan, screenshot_path=screenshot_path)
        newly_completed = set(data.get("newly_completed", []))
        still_missing = set(data.get("still_missing", []))
        report.scene_description = data.get("scene_description", "")
        report.model_used = "vision"

        for obj in plan.objects:
            name = obj["name"]
            name_lower = name.lower()

            if name_lower in {n.lower() for n in newly_completed} or name_lower in {n.lower() for n in completed}:
                status = ObjectStatus.DRAWN
            elif name_lower in {n.lower() for n in still_missing}:
                status = ObjectStatus.MISSING
            else:
                # Check previous status
                prev_assessment = next(
                    (a for a in previous.assessments if a.name.lower() == name_lower),
                    None,
                )
                status = prev_assessment.status if prev_assessment else ObjectStatus.PENDING

            report.assessments.append(ObjectAssessment(
                name=name,
                status=status,
                requested_color=obj.get("color", ""),
            ))

        # Update match score
        if report.assessments:
            done_count = len([a for a in report.assessments if a.status == ObjectStatus.DRAWN])
            report.overall_match = done_count / len(report.assessments)

        report.validation_time_ms = (time.time() - t0) * 1000

        if verbose:
            self._print_report(report)

        return report

    # ── Validate from screenshot file ─────────────────────────────────

    async def validate_screenshot(
        self,
        screenshot_path: str,
        plan: TaskPlan,
        verbose: bool = False,
    ) -> ValidationReport:
        """Validate an existing screenshot file against a plan."""
        return await self.validate(screenshot_path, plan, verbose=verbose)

    # ── Helper: plan from NL description ──────────────────────────────

    @staticmethod
    def plan_from_description(description: str) -> TaskPlan:
        """
        Create a TaskPlan from a natural language description.
        Uses DrawingSkill's NL parser to detect shapes and colors.
        """
        try:
            from nlp2cmd.skills.drawing.skill import DrawingSkill
            skill = DrawingSkill()
            shape = skill.detect_shape(description)
            color = skill.detect_color(description, default="")

            plan = TaskPlan(description=description)
            if shape:
                plan.add(shape, color)
            return plan
        except Exception:
            return TaskPlan(description=description)

    # ── Internal ──────────────────────────────────────────────────────

    async def _get_screenshot(self, page_or_screenshot) -> tuple[str | None, str]:
        """Get base64 screenshot from page or file path."""
        if isinstance(page_or_screenshot, (str, Path)):
            path = Path(page_or_screenshot)
            if path.exists():
                b64 = base64.b64encode(path.read_bytes()).decode()
                return b64, str(path)
            return None, str(path)

        # Assume it's a Playwright page
        try:
            screenshot_bytes = await page_or_screenshot.screenshot()
            b64 = base64.b64encode(screenshot_bytes).decode()
            return b64, "(live page)"
        except Exception:
            return None, ""

    async def _vision_call(self, b64: str, prompt: str) -> dict | None:
        """Call vision model and return parsed JSON."""
        if not self._use_vision:
            return None

        router = self._get_router()
        if router is None:
            return None

        for attempt in range(self._max_retries + 1):
            try:
                resp = await router.route_call(
                    prompt=prompt,
                    task_category="vision",
                    images=[b64],
                    timeout=30,
                )
                if resp and resp.text:
                    data = self._parse_json(resp.text)
                    if data:
                        return data
            except Exception:
                continue

        return None

    def _heuristic_validate(self, plan: TaskPlan, screenshot_path: str,
                            t0: float) -> ValidationReport:
        """Heuristic fallback when vision is unavailable."""
        report = ValidationReport(
            plan=plan,
            screenshot_path=screenshot_path,
            model_used="heuristic",
        )

        # Check screenshot file size as rough proxy
        try:
            size = Path(screenshot_path).stat().st_size if screenshot_path else 0
            if size < 5000:
                # Tiny file = likely blank canvas
                for obj in plan.objects:
                    report.assessments.append(ObjectAssessment(
                        name=obj["name"],
                        status=ObjectStatus.MISSING,
                        requested_color=obj.get("color", ""),
                        confidence=0.3,
                    ))
            else:
                # Something was drawn — mark all as partial (uncertain)
                for obj in plan.objects:
                    report.assessments.append(ObjectAssessment(
                        name=obj["name"],
                        status=ObjectStatus.PARTIAL,
                        requested_color=obj.get("color", ""),
                        confidence=0.2,
                        issue="Vision unavailable — cannot confirm",
                    ))
        except Exception:
            for obj in plan.objects:
                report.assessments.append(ObjectAssessment(
                    name=obj["name"],
                    status=ObjectStatus.PENDING,
                    requested_color=obj.get("color", ""),
                ))

        report.validation_time_ms = (time.time() - t0) * 1000
        return report

    def _print_report(self, report: ValidationReport) -> None:
        """Pretty-print validation report."""
        icons = {
            ObjectStatus.DRAWN: "✅",
            ObjectStatus.MISSING: "⬜",
            ObjectStatus.WRONG: "❌",
            ObjectStatus.PARTIAL: "⚠️",
            ObjectStatus.PENDING: "⏳",
        }

        print(f"\n  📊 Validation: {report.summary()}")
        if report.scene_description:
            print(f"  👁️ Scene: {report.scene_description[:100]}")

        for a in report.assessments:
            icon = icons.get(a.status, "?")
            color_info = f" ({a.requested_color})" if a.requested_color else ""
            extra = f" — {a.issue}" if a.issue else ""
            print(f"  {icon} {a.name}{color_info}: {a.status.value}{extra}")

        if report.next_actions():
            print(f"  📋 Next: {'; '.join(report.next_actions()[:3])}")

    @staticmethod
    def _parse_json(text: str) -> dict | None:
        from nlp2cmd.skills.drawing.llm_helpers import parse_llm_json_object
        return parse_llm_json_object(text)
