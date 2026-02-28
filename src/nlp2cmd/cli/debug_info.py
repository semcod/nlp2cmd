"""
Debug info module for nlp2cmd CLI.

Provides functions to show schemas and decision tree information
for debugging and understanding the pipeline.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from rich.console import Console


def show_schema_info(console: Optional["Console"] = None) -> None:
    """Show available schemas (intents, entities, templates) as markdown."""
    if console is None:
        from rich.console import Console
        console = Console()

    # Load intent matcher
    from nlp2cmd.nlp.intent_matcher import IntentMatcher
    matcher = IntentMatcher()

    # Get pipeline templates
    from nlp2cmd.generation.template_generator import TemplateGenerator
    generator = TemplateGenerator()

    # Load entities
    from nlp2cmd.utils.data_files import find_data_file
    from nlp2cmd.utils.yaml_compat import yaml
    entities_path = find_data_file(explicit_path=None, default_filename="entities/apps.yaml")
    entities_data = {}
    if entities_path and entities_path.exists():
        try:
            with open(entities_path, "r", encoding="utf-8") as f:
                entities_data = yaml.safe_load(f) or {}
        except Exception:
            pass

    console.print("# Available Schemas for NLP2CMD\n")

    # Intents section
    console.print("## 📋 Registered Intents\n")
    intents = matcher.list_intents()
    console.print(f"**Total intents:** {len(intents)}\n")

    for intent_name in intents:
        intent_def = matcher.get_intent(intent_name)
        if intent_def:
            console.print(f"### {intent_name}")
            console.print(f"- **Domain:** {intent_def.domain}")
            console.print(f"- **Description:** {intent_def.description}")

            # Labels by language
            for lang, labels in intent_def.labels.items():
                label_list = ", ".join(f"`{l}`" for l in labels[:5])
                if len(labels) > 5:
                    label_list += f" (and {len(labels) - 5} more)"
                console.print(f"- **Labels ({lang}):** {label_list}")

            # Entities
            if intent_def.entities:
                entity_list = ", ".join(f"`{e.get('name', '?')}`" for e in intent_def.entities)
                console.print(f"- **Entities:** {entity_list}")

            console.print()

    # Entities section
    console.print("## 📦 Registered Entities\n")
    apps = entities_data.get("apps", {})
    console.print(f"**Total applications:** {len(apps)}\n")

    for app_name, app_data in apps.items():
        console.print(f"### {app_name}")
        console.print(f"- **Launch command:** `{app_data.get('launch', 'N/A')}`")
        console.print(f"- **Process:** `{app_data.get('process', 'N/A')}`")
        aliases = app_data.get("aliases", {})
        for lang, alias_list in aliases.items():
            alias_str = ", ".join(f"`{a}`" for a in alias_list[:5])
            if len(alias_list) > 5:
                alias_str += f" (and {len(alias_list) - 5} more)"
            console.print(f"- **Aliases ({lang}):** {alias_str}")
        console.print()

    # Templates section
    console.print("## 📝 Available Templates\n")
    templates = getattr(generator, "templates", {})
    console.print(f"**Total template domains:** {len(templates)}\n")

    for domain, domain_templates in templates.items():
        console.print(f"### Domain: {domain}")
        console.print(f"**Intents:** {len(domain_templates)}")
        for intent_name in list(domain_templates.keys())[:10]:
            console.print(f"- `{intent_name}`")
        if len(domain_templates) > 10:
            console.print(f"- ... and {len(domain_templates) - 10} more")
        console.print()


def show_decision_tree_info(query: str, console: Optional["Console"] = None) -> None:
    """Show decision tree for a query - step by step pipeline decisions."""
    if console is None:
        from rich.console import Console
        console = Console()

    console.print(f"# Decision Tree for Query: \"{query}\"\n")

    # Step 1: Intent detection
    console.print("## Step 1: Intent Detection\n")

    from nlp2cmd.nlp.intent_matcher import IntentMatcher
    matcher = IntentMatcher()
    matches = matcher.match(query, top_k=5)

    console.print("### Top Intent Matches:")
    for i, match in enumerate(matches, 1):
        confidence_emoji = "🟢" if match.confidence > 0.8 else "🟡" if match.confidence > 0.5 else "🔴"
        console.print(f"{i}. {confidence_emoji} **{match.intent}** (confidence: {match.confidence:.2f})")
        console.print(f"   - Domain: `{match.domain}`")
        console.print(f"   - Method: `{match.method}`")
        console.print(f"   - Matched label: `{match.matched_label}` ({match.matched_lang})")
        console.print()

    if not matches:
        console.print("🔴 **No intent matches found!**\n")

    # Step 2: Run through pipeline
    console.print("## Step 2: Pipeline Processing\n")

    from nlp2cmd.generation.pipeline import RuleBasedPipeline
    pipeline = RuleBasedPipeline()

    result = pipeline.process(query)

    console.print("### Detection Result:")
    console.print(f"- **Domain:** `{result.domain}`")
    console.print(f"- **Intent:** `{result.intent}`")
    console.print(f"- **Detection Confidence:** {result.detection_confidence:.2f}")
    console.print(f"- **Source:** `{result.source}`")
    console.print()

    # Step 3: Entities
    console.print("## Step 3: Entity Extraction\n")

    if result.entities:
        console.print("### Extracted Entities:")
        for entity_name, entity_value in result.entities.items():
            console.print(f"- `{entity_name}`: `{entity_value}`")
    else:
        console.print("🔴 **No entities extracted!**")
    console.print()

    # Step 4: Command generation
    console.print("## Step 4: Command Generation\n")

    console.print(f"- **Template Used:** `{result.template_used or 'N/A'}`")
    console.print(f"- **Final Confidence:** {result.confidence:.2f}")
    console.print()

    # Step 5: Final result
    console.print("## Step 5: Final Result\n")

    if result.success:
        console.print(f"✅ **Success!** Generated command:")
        console.print(f"```bash\n{result.command}\n```")
    else:
        console.print(f"❌ **Failed!**")
        console.print(f"- **Generated command:** `{result.command or 'None'}`")
        if result.errors:
            console.print("- **Errors:**")
            for error in result.errors:
                console.print(f"  - {error}")
        if result.warnings:
            console.print("- **Warnings:**")
            for warning in result.warnings:
                console.print(f"  - {warning}")
    console.print()

    # Metadata
    console.print("## Metadata\n")
    console.print(f"- **Latency:** {result.latency_ms:.1f} ms")
    if result.metadata:
        console.print("- **Additional Metadata:**")
        for key, value in result.metadata.items():
            console.print(f"  - `{key}`: {value}")

    # Multi-step info
    if hasattr(result, "action_plan") and result.action_plan:
        console.print("\n## Multi-Step Action Plan\n")
        plan = result.action_plan
        console.print(f"- **Steps:** {len(plan.steps) if hasattr(plan, 'steps') else 'N/A'}")
        console.print(f"- **Plan Source:** `{getattr(plan, 'source', 'N/A')}`")
        console.print(f"- **Plan Confidence:** {getattr(plan, 'confidence', 0):.2f}")


def generate_debug_log_md(query: str, output_path: str) -> None:
    """Generate comprehensive debug log in markdown format."""
    import io
    from datetime import datetime
    from rich.console import Console

    # Create string buffer for markdown output
    buffer = io.StringIO()
    console = Console(file=buffer, force_terminal=False, color_system=None)

    # Header
    console.print(f"# NLP2CMD Debug Log\n")
    console.print(f"**Generated:** {datetime.now().isoformat()}\n")
    console.print(f"**Query:** `{query}`\n")

    # Show decision tree
    show_decision_tree_info(query, console)

    # Get markdown content
    markdown_content = buffer.getvalue()

    # Write to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    print(f"Debug log written to: {output_path}")
