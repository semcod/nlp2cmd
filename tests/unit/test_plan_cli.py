"""Tests for nlp2cmd plan CLI options."""

from __future__ import annotations

from click.testing import CliRunner

import nlp2cmd.cli.main as cli_main


def test_plan_help_lists_explain_and_dry_run() -> None:
    runner = CliRunner()
    result = runner.invoke(cli_main.main, ["plan", "--help"])
    assert result.exit_code == 0
    assert "--explain" in result.output
    assert "--dry-run" in result.output
    assert "--execute" in result.output
