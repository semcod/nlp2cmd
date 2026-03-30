# Dynamic Schemas Examples

This folder collects examples for schema extraction, version-aware generation, persistent storage, and schema-flow demos.

## Included examples

- `example.py` — dynamic sources demo for shell scripts and Makefiles
- `demo_enhanced.py` — enhanced schema extraction and pipeline demo
- `demo_intelligent_nlp2cmd.py` — version-aware NLP2CMD example
- `demo_persistent_storage.py` — per-command schema storage demo
- `demo_schema_flow.py` — schema-to-command flow walkthrough
- `demo_version_detection.py` — practical version-aware command generation
- `schema_flow_demo.py` — full schema extraction and usage flow
- `simple_schema_demo.py` — minimal schema walkthrough

## Run

```bash
python example.py
python demo_schema_flow.py
python demo_version_detection.py
```

Most scripts expect to be run from the repository checkout and use `src/` via the local `sys.path` setup.
