#!/usr/bin/env python3
"""
NLP2CMD Feedback Loop Example

Demonstrates the interactive feedback loop with:
- Error detection and analysis
- Automatic corrections
- User-guided refinement
- Confidence-based decisions
"""

import sys
from pathlib import Path

from nlp2cmd import NLP2CMD, SQLAdapter, FeedbackAnalyzer
from nlp2cmd.feedback import CorrectionEngine, FeedbackType
from nlp2cmd.validators import SQLValidator

sys.path.append(str(Path(__file__).resolve().parents[2]))

from _example_helpers import print_rule, print_separator


def _print_feedback(query: str, command: str, feedback) -> None:
    print(f"\n📝 Input: {query}")
    print(f"📤 Generated: {command}")
    print(f"📊 Status: {feedback.type.value}")
    print(f"🎯 Confidence: {feedback.confidence:.0%}")


def _scenario_success(analyzer: FeedbackAnalyzer, adapter: SQLAdapter, validator: SQLValidator) -> None:
    print_rule(width=70, char="─", leading_newline=True)
    print("Scenario 1: Successful Transformation")
    print_rule(width=70, char="─")

    query = "Show all active users"
    plan = {
        "intent": "select",
        "entities": {
            "table": "users",
            "columns": "*",
            "filters": [{"field": "status", "operator": "=", "value": "active"}],
        },
    }
    command = adapter.generate(plan)
    feedback = analyzer.analyze(
        original_input=query,
        generated_output=command,
        validation_errors=validator.validate(command).errors,
        validation_warnings=validator.validate(command).warnings,
        dsl_type="sql",
    )
    _print_feedback(query, command, feedback)
    if feedback.is_success:
        print("✅ Transformation successful!")


def _scenario_warnings(analyzer: FeedbackAnalyzer, adapter: SQLAdapter, validator: SQLValidator) -> None:
    print_rule(width=70, char="─", leading_newline=True)
    print("Scenario 2: Transformation with Warnings")
    print_rule(width=70, char="─")

    query = "Update all users to premium"
    plan = {
        "intent": "update",
        "entities": {"table": "users", "values": {"status": "premium"}, "filters": []},
    }
    command = adapter.generate(plan)
    validation = validator.validate(command)
    feedback = analyzer.analyze(
        original_input=query,
        generated_output=command,
        validation_errors=validation.errors,
        validation_warnings=validation.warnings,
        dsl_type="sql",
    )
    _print_feedback(query, command, feedback)
    if feedback.warnings:
        print("\n⚠️  Warnings:")
        for warning in feedback.warnings:
            print(f"   - {warning}")
    if feedback.suggestions:
        print("\n💡 Suggestions:")
        for suggestion in feedback.suggestions:
            print(f"   - {suggestion}")


def _scenario_auto_correction(analyzer: FeedbackAnalyzer, correction_engine: CorrectionEngine) -> None:
    print_rule(width=70, char="─", leading_newline=True)
    print("Scenario 3: Syntax Error with Auto-Correction")
    print_rule(width=70, char="─")

    bad_command = "SELECT * FROM users WHERE (status = 'active'"
    syntax_check = analyzer.check_syntax(bad_command, "sql")
    print(f"\n📝 Command: {bad_command}")
    print(f"✓ Valid: {syntax_check['valid']}")

    for error in syntax_check.get("errors", []):
        print(f"\n❌ Errors:\n   - {error}")
        correction = correction_engine.suggest(error, bad_command, {"dsl_type": "sql"})
        if not correction.get("fix"):
            continue
        print(f"\n🔧 Suggested fix (confidence: {correction['confidence']:.0%}):")
        print(f"   {correction['fix']}")
        if correction["confidence"] >= 0.8:
            print("   ✅ Auto-applying fix...")
            corrected = correction_engine.apply_correction(bad_command, correction)
            print(f"   Corrected: {corrected}")


def _scenario_ambiguous(analyzer: FeedbackAnalyzer) -> None:
    print_rule(width=70, char="─", leading_newline=True)
    print("Scenario 4: Ambiguous Input")
    print_rule(width=70, char="─")

    query = "Delete that thing"
    feedback = analyzer.analyze(original_input=query, generated_output="", dsl_type="sql", context=None)
    _print_feedback(query, "", feedback)
    if feedback.requires_user_input:
        print("\n❓ Clarification needed:")
        for question in feedback.clarification_questions:
            print(f"   - {question}")


def _scenario_exceptions(analyzer: FeedbackAnalyzer) -> None:
    print_rule(width=70, char="─", leading_newline=True)
    print("Scenario 5: Exception Analysis")
    print_rule(width=70, char="─")

    exceptions = [
        FileNotFoundError("Table 'customers' does not exist"),
        PermissionError("Access denied for user 'readonly'@'localhost'"),
        ConnectionError("Could not connect to database server"),
        TimeoutError("Query execution timed out after 30s"),
    ]
    for exc in exceptions:
        analysis = analyzer.analyze_exception(exc)
        print(f"\n❌ Exception: {analysis['error_type']}")
        print(f"   Message: {analysis['error_message']}")
        if analysis["suggestions"]:
            print("   💡 Suggestions:")
            for suggestion in analysis["suggestions"]:
                print(f"      - {suggestion}")


def _scenario_refinement() -> None:
    print_rule(width=70, char="─", leading_newline=True)
    print("Scenario 6: Iterative Refinement")
    print_rule(width=70, char="─")
    print("\nSimulating iterative refinement process:")

    iterations = [
        ("Show sales", "Ambiguous - which table?", "Show sales from orders"),
        ("Show sales from orders", "Missing time filter", "Show sales from orders this month"),
        ("Show sales from orders this month", "Success!", None),
    ]
    for i, (input_text, feedback_text, refined) in enumerate(iterations, 1):
        print(f"\n   Iteration {i}:")
        print(f"   Input: {input_text}")
        print(f"   Feedback: {feedback_text}")
        print(f"   → Refined: {refined}" if refined else "   ✅ Final result achieved!")


def _print_summary() -> None:
    print_separator("FEEDBACK LOOP SUMMARY", leading_newline=True, width=70)
    print("""
The NLP2CMD Feedback Loop provides status classification, auto-correction,
suggestions, clarification questions, and confidence scoring.
""")


def simulate_interactive_session():
    """Simulate an interactive session with feedback loop."""
    print_separator("NLP2CMD Feedback Loop Demonstration", width=70)

    adapter = SQLAdapter(
        dialect="postgresql",
        schema_context={
            "tables": ["users", "orders", "products"],
            "columns": {
                "users": ["id", "name", "email", "status"],
                "orders": ["id", "user_id", "total", "status"],
                "products": ["id", "name", "price", "stock"],
            },
        },
    )
    analyzer = FeedbackAnalyzer()
    validator = SQLValidator()
    correction_engine = CorrectionEngine()

    NLP2CMD(adapter=adapter, feedback_analyzer=analyzer, validator=validator)

    _scenario_success(analyzer, adapter, validator)
    _scenario_warnings(analyzer, adapter, validator)
    _scenario_auto_correction(analyzer, correction_engine)
    _scenario_ambiguous(analyzer)
    _scenario_exceptions(analyzer)
    _scenario_refinement()
    _print_summary()


if __name__ == "__main__":
    simulate_interactive_session()
