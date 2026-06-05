#!/usr/bin/env python3
"""NLP2CMD Environment Analysis Example."""

import sys
from pathlib import Path

from nlp2cmd.environment import EnvironmentAnalyzer

sys.path.append(str(Path(__file__).resolve().parents[2]))

from _environment_sections import (
    print_command_validation,
    print_config_files,
    print_export_preview,
    print_full_report,
    print_resources,
    print_service_status,
    print_system_info,
    print_tool_detection,
)
from _example_helpers import print_separator


def main():
    print_separator("NLP2CMD Environment Analysis", width=70)
    analyzer = EnvironmentAnalyzer()
    env = analyzer.analyze()

    print_system_info(env)
    tools = print_tool_detection(analyzer)
    services = print_service_status(analyzer)
    configs = print_config_files(analyzer)
    disk, memory = print_resources(analyzer)
    print_command_validation(analyzer, services)
    report = print_full_report(analyzer)
    print_export_preview(report)

    print_separator("ENVIRONMENT ANALYSIS SUMMARY", leading_newline=True, width=70)
    available_count = len([t for t in tools.values() if t.available])
    running_count = len([s for s in services.values() if s.running])
    print(f"""
📊 Analysis Results:

   System: {env['os']['system']} {env['os']['release']}
   Tools:  {available_count}/{len(tools)} available
   Services: {running_count}/{len(services)} running
   Disk: {disk.get('percent_used', 0.0):.0f}% used
   Memory: {(memory or {}).get('percent_used', 0.0):.0f}% used (if available)
   Config files: {len(configs)} found
   Recommendations: {len(report.recommendations)}
""")


if __name__ == "__main__":
    main()
