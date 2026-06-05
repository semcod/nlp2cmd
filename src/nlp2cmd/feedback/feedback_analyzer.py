# FeedbackAnalyzer - extracted from __init__.py
"""
Feedback Loop module for NLP2CMD.

Provides intelligent feedback analysis, error correction suggestions,
and iterative improvement capabilities.
"""
from __future__ import annotations
import logging
import re
import shlex
import shutil
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional
logger = logging.getLogger(__name__)
from nlp2cmd.feedback.correction_rule import CorrectionRule
from nlp2cmd.feedback.feedback_result import FeedbackResult
from nlp2cmd.feedback.feedback_type import FeedbackType

class FeedbackAnalyzer:
    """
    Analyzes transformation results and provides feedback.

    This class examines errors, warnings, and the generated output
    to provide actionable feedback and correction suggestions.
    """

    def __init__(self, correction_rules: Optional[list[CorrectionRule]] = None):
        """
        Initialize the analyzer.

        Args:
            correction_rules: Custom correction rules
        """
        self.correction_rules = correction_rules or []
        self._register_default_rules()

    def _register_default_rules(self):
        """Register default correction rules."""
        default_rules = [
            # SQL rules
            CorrectionRule(
                pattern=r"DELETE FROM (\w+)\s*;",
                replacement=r"DELETE FROM \1 WHERE /* add condition */;",
                description="Add WHERE clause to DELETE",
                confidence=0.85,
                applies_to=["sql"],
            ),
            CorrectionRule(
                pattern=r"UPDATE (\w+) SET (.+);$",
                replacement=r"UPDATE \1 SET \2 WHERE /* add condition */;",
                description="Add WHERE clause to UPDATE",
                confidence=0.85,
                applies_to=["sql"],
            ),
            # Shell rules
            CorrectionRule(
                pattern=r"rm -rf (\S+)",
                replacement=r"rm -ri \1",
                description="Use interactive mode for rm",
                confidence=0.7,
                applies_to=["shell"],
            ),
            # Docker rules
            CorrectionRule(
                pattern=r"docker run (.+) (\w+)$",
                replacement=r"docker run \1 \2:latest",
                description="Add :latest tag to image",
                confidence=0.8,
                applies_to=["docker"],
            ),
        ]
        self.correction_rules.extend(default_rules)

    def analyze(
        self,
        original_input: str,
        generated_output: str,
        validation_errors: Optional[list[str]] = None,
        validation_warnings: Optional[list[str]] = None,
        dsl_type: str = "unknown",
        context: Optional[dict[str, Any]] = None,
    ) -> FeedbackResult:
        """
        Analyze transformation result and generate feedback.

        Args:
            original_input: Original natural language input
            generated_output: Generated command/output
            validation_errors: Errors from validation
            validation_warnings: Warnings from validation
            dsl_type: Type of DSL (sql, shell, docker, etc.)
            context: Additional context

        Returns:
            FeedbackResult with analysis
        """
        errors = list(validation_errors or [])
        warnings = list(validation_warnings or [])
        suggestions = []
        auto_corrections = {}
        clarification_questions = []

        ctx = context or {}
        last_plan = ctx.get("last_plan") if isinstance(ctx, dict) else None
        plan_confidence: Optional[float] = None
        if isinstance(last_plan, dict):
            try:
                plan_confidence = float(last_plan.get("confidence"))  # type: ignore[arg-type]
            except (TypeError, ValueError):
                plan_confidence = None

        transform_status = ctx.get("transform_status") if isinstance(ctx, dict) else None

        # Determine feedback type
        if errors:
            feedback_type = FeedbackType.SYNTAX_ERROR
        elif warnings:
            feedback_type = FeedbackType.PARTIAL_SUCCESS
        else:
            feedback_type = FeedbackType.SUCCESS

        output_str = str(generated_output or "")
        output_strip = output_str.strip()

        if not output_strip:
            if feedback_type == FeedbackType.SUCCESS:
                feedback_type = FeedbackType.AMBIGUOUS_INPUT
            clarification_questions.append("I could not generate a command. What exactly should be done (and on which target)?")

        if isinstance(transform_status, str) and transform_status.lower() == "blocked":
            feedback_type = FeedbackType.SECURITY_VIOLATION
            if not clarification_questions:
                clarification_questions.append("This command was blocked by the safety policy. Do you want to proceed anyway?")
            suggestions.append("Consider running in dry-run mode or narrowing the scope of the operation.")

        # Analyze errors and generate suggestions
        for error in errors:
            error_analysis = self._analyze_error(error, generated_output, dsl_type)
            suggestions.extend(error_analysis.get("suggestions", []))
            auto_corrections.update(error_analysis.get("auto_corrections", {}))
            clarification_questions.extend(error_analysis.get("questions", []))

        if output_strip.startswith("#") and "no matching command found" in output_strip.lower():
            feedback_type = FeedbackType.SCHEMA_MISMATCH
            msg = output_strip.lstrip("#").strip()
            if msg and msg not in errors:
                errors.append(msg)
            clarification_questions.extend(
                [
                    "Which tool/domain should be used (shell/docker/kubernetes/appspec)?",
                    "If you expected a specific base command, what is it (e.g. docker, kubectl, nginx)?",
                ]
            )
            suggestions.append("You can generate/extend schemas via app2schema and re-run.")

        missing_tool: Optional[str] = None
        if dsl_type in {"shell", "docker", "kubernetes", "dynamic", "appspec", "auto"}:
            missing_tool = self._detect_missing_tool(output_strip, ctx)
            if missing_tool:
                feedback_type = FeedbackType.RUNTIME_ERROR
                err = f"Required tool is not available: {missing_tool}"
                if err not in errors:
                    errors.append(err)
                clarification_questions.append(
                    f"Do you want installation instructions for '{missing_tool}'? If yes, which distro/package manager do you use?"
                )
                suggestions.append(f"Install '{missing_tool}' and try again.")

        if dsl_type in {"shell", "docker", "kubernetes", "dynamic", "appspec", "auto"}:
            placeholders = self._detect_placeholders(output_strip)
            if placeholders:
                if feedback_type == FeedbackType.SUCCESS:
                    feedback_type = FeedbackType.AMBIGUOUS_INPUT
                clarification_questions.append("I need a few details to fill the command template: " + ", ".join(placeholders))

        if (
            feedback_type == FeedbackType.SUCCESS
            and plan_confidence is not None
            and plan_confidence < 0.35
        ):
            feedback_type = FeedbackType.AMBIGUOUS_INPUT
            clarification_questions.append("I am not confident about the intent. What exactly should the command do?")

        # Try to apply correction rules
        for rule in self.correction_rules:
            if rule.applies_to and dsl_type not in rule.applies_to:
                continue

            match = re.search(rule.pattern, generated_output)
            if match:
                if callable(rule.replacement):
                    fixed = rule.replacement(match)
                else:
                    fixed = re.sub(rule.pattern, rule.replacement, generated_output)

                if rule.confidence >= 0.9:
                    auto_corrections[generated_output] = fixed
                else:
                    suggestions.append(f"💡 {rule.description}: {fixed}")

        # Check for ambiguous input
        if feedback_type == FeedbackType.SUCCESS and self._is_ambiguous(original_input, context):
            feedback_type = FeedbackType.AMBIGUOUS_INPUT
            clarification_questions.extend(
                self._generate_clarification_questions(original_input, dsl_type)
            )

        # Calculate confidence
        confidence = self._calculate_confidence(
            errors, warnings, len(auto_corrections), generated_output
        )

        metadata: dict[str, Any] = {}
        if plan_confidence is not None:
            metadata["plan_confidence"] = plan_confidence
        if isinstance(transform_status, str):
            metadata["transform_status"] = transform_status
        if missing_tool:
            metadata["missing_tool"] = missing_tool

        return FeedbackResult(
            type=feedback_type,
            original_input=original_input,
            generated_output=generated_output,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            auto_corrections=auto_corrections,
            confidence=confidence,
            requires_user_input=len(clarification_questions) > 0,
            clarification_questions=clarification_questions,
            metadata=metadata,
        )

    def _detect_missing_tool(self, output: str, context: dict[str, Any]) -> Optional[str]:
        if not output or output.startswith("#"):
            return None

        try:
            parts = shlex.split(output)
        except Exception:
            parts = output.split()

        if not parts:
            return None

        # Handle sudo wrapper.
        tool = parts[0]
        if tool == "sudo" and len(parts) >= 2:
            tool = parts[1]

        if shutil.which(tool) is None:
            return tool

        return None

    def _detect_placeholders(self, output: str) -> list[str]:
        if not output or output.startswith("#"):
            return []

        if "{" not in output or "}" not in output:
            return []

        try:
            parts = shlex.split(output)
        except Exception:
            parts = output.split()

        if not parts:
            return []

        tool = parts[0]
        if tool == "sudo" and len(parts) >= 2:
            tool = parts[1]

        templated_tools = {"docker", "kubectl", "helm", "terraform", "git", "nginx"}
        if tool not in templated_tools:
            return []

        return sorted(set(re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", output)))

    def _analyze_error(
        self,
        error: str,
        output: str,
        dsl_type: str,
    ) -> dict[str, Any]:
        """Analyze a specific error and generate suggestions."""
        suggestions = []
        auto_corrections = {}
        questions = []

        error_lower = error.lower()

        # Common error patterns
        if "unbalanced" in error_lower or "unclosed" in error_lower:
            if "parenthes" in error_lower:
                suggestions.append("Check for missing opening or closing parenthesis")
            elif "quote" in error_lower:
                suggestions.append("Check for missing quotation marks")
            elif "brace" in error_lower:
                suggestions.append("Check for missing curly braces")

        if "not found" in error_lower or "unknown" in error_lower:
            if "table" in error_lower:
                questions.append("Which table did you mean to query?")
            elif "command" in error_lower:
                questions.append("Is the required tool installed?")
            elif "column" in error_lower:
                questions.append("Which column did you intend to use?")

        if "permission" in error_lower or "access denied" in error_lower:
            suggestions.append("You may need elevated privileges (sudo) for this operation")

        return {
            "suggestions": suggestions,
            "auto_corrections": auto_corrections,
            "questions": questions,
        }

    def _is_ambiguous(
        self,
        input_text: str,
        context: Optional[dict[str, Any]],
    ) -> bool:
        """Check if input is ambiguous."""
        ambiguous_indicators = [
            "to", "that thing", "the file", "my project",
            "it", "them", "those", "these",
        ]

        input_lower = input_text.lower()

        # Check for pronouns without clear referent
        for indicator in ambiguous_indicators:
            if indicator in input_lower:
                # If no context provided, it's ambiguous
                if not context:
                    return True
                # If context doesn't have previous references, it's ambiguous
                if "previous_commands" not in context and "previous_topics" not in context:
                    return True

        return False

    def _generate_clarification_questions(
        self,
        input_text: str,
        dsl_type: str,
    ) -> list[str]:
        """Generate clarification questions for ambiguous input."""
        questions = []

        input_lower = input_text.lower()

        if "the file" in input_lower or "that file" in input_lower:
            questions.append("Which file are you referring to?")

        if "the table" in input_lower or "that table" in input_lower:
            questions.append("Which database table did you mean?")

        if "delete" in input_lower or "remove" in input_lower:
            questions.append("Can you confirm what you want to delete?")

        if "all" in input_lower:
            questions.append("When you say 'all', which specific items do you mean?")

        return questions

    def _calculate_confidence(
        self,
        errors: list[str],
        warnings: list[str],
        auto_fix_count: int,
        output: str,
    ) -> float:
        """Calculate confidence score."""
        confidence = 1.0

        # Reduce confidence for errors
        confidence -= len(errors) * 0.2

        # Slightly reduce for warnings
        confidence -= len(warnings) * 0.05

        # Increase slightly for auto-fixes available
        if auto_fix_count > 0:
            confidence += 0.05

        # Reduce for very short or very long output
        if len(output) < 10:
            confidence -= 0.1
        elif len(output) > 1000:
            confidence -= 0.05

        return max(0.0, min(1.0, confidence))

    def check_syntax(self, content: str, dsl_type: str) -> dict[str, Any]:
        """Quick syntax check for content."""
        errors = []

        # Basic checks
        if content.count("(") != content.count(")"):
            errors.append("Unbalanced parentheses")
        if content.count("[") != content.count("]"):
            errors.append("Unbalanced brackets")
        if content.count("{") != content.count("}"):
            errors.append("Unbalanced braces")

        # Quote checks
        single_quotes = content.count("'") - content.count("\\'")
        double_quotes = content.count('"') - content.count('\\"')

        if single_quotes % 2 != 0:
            errors.append("Unclosed single quote")
        if double_quotes % 2 != 0:
            errors.append("Unclosed double quote")

        return {"valid": len(errors) == 0, "errors": errors}

    def analyze_exception(self, exception: Exception) -> dict[str, Any]:
        """Analyze an exception and provide suggestions."""
        error_msg = str(exception)
        error_type = type(exception).__name__

        suggestions = []
        questions = []

        # Common exception patterns
        if "FileNotFoundError" in error_type or "No such file" in error_msg:
            suggestions.append("Check if the file path is correct")
            suggestions.append("Verify the file exists")
            questions.append("What is the correct file path?")

        elif "PermissionError" in error_type:
            suggestions.append("Try running with elevated privileges")
            suggestions.append("Check file/directory permissions")

        elif "ConnectionError" in error_type or "timeout" in error_msg.lower():
            suggestions.append("Check network connectivity")
            suggestions.append("Verify the service is running")

        elif "SyntaxError" in error_type:
            suggestions.append("Review command syntax")
            suggestions.append("Check for typos or missing elements")

        return {
            "suggestions": suggestions,
            "questions": questions,
            "error_type": error_type,
            "error_message": error_msg,
        }
