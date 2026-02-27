import pytest


def test_run_mode_sql_does_not_execute_shell(monkeypatch):
    import importlib

    cli_main = importlib.import_module("nlp2cmd.cli.main")

    created = {"runner": False}

    class FakeRunner:
        def __init__(self, *args, **kwargs):
            created["runner"] = True

        def run_with_recovery(self, *args, **kwargs):
            raise AssertionError("SQL should not be executed as a shell command in --run mode")

    monkeypatch.setattr(cli_main, "ExecutionRunner", FakeRunner)

    cli_main._handle_run_query(
        "Pokaż użytkowników",
        dsl="auto",
        appspec=None,
        auto_confirm=True,
        no_submit=False,
        execute_web=False,
        auto_install=False,
        auto_repair=False,
    )

    assert created["runner"] is False


def test_run_mode_sql_only_multistep_does_not_execute_shell(monkeypatch):
    import importlib

    cli_main = importlib.import_module("nlp2cmd.cli.main")

    created = {"runner": False}

    class FakeRunner:
        def __init__(self, *args, **kwargs):
            created["runner"] = True

        def run_with_recovery(self, *args, **kwargs):
            raise AssertionError("SQL steps should not be executed as a shell command in --run mode")

    monkeypatch.setattr(cli_main, "ExecutionRunner", FakeRunner)

    cli_main._handle_run_query(
        "Pokaż użytkowników. Pokaż tabele.",
        dsl="auto",
        appspec=None,
        auto_confirm=True,
        no_submit=False,
        execute_web=False,
        auto_install=False,
        auto_repair=False,
    )

    assert created["runner"] is False
