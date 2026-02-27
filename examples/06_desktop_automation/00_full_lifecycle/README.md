# 00 — Full Lifecycle: Setup → Test → Analyze → Teardown

End-to-end automation lifecycle: start the Docker desktop environment,
run all bash examples (01-05), collect markdown logs with screenshots,
generate a summary report, and stop the environment.

## What it does

1. **Setup** — `docker compose up` for noVNC + XFCE desktop
2. **Wait** — Poll until noVNC canvas is ready
3. **Run examples** — Execute 01_terminal through 05_email_client
4. **Analyze** — Collect all `logs/session.md`, count steps & screenshots
5. **Report** — Generate `results/summary.md` with pass/fail per example
6. **Teardown** — `docker compose down`

## Run

```bash
cd examples/06_desktop_automation/00_full_lifecycle
bash run.sh
```

## Options

```bash
bash run.sh --skip-setup      # Skip Docker startup (env already running)
bash run.sh --skip-teardown   # Leave Docker running after tests
bash run.sh --only 01 03      # Run only specific examples
```

## Output

```
results/
├── summary.md          # Overall report with pass/fail
├── 01_terminal.log     # stdout/stderr from each example
├── 02_calculator.log
├── 03_text_editor.log
├── 04_browser_tabs.log
└── 05_email_client.log
```

Each example's own `logs/session.md` also contains screenshots.
