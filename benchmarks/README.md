# NLP2CMD Benchmarks

This folder contains the benchmark runners that are being separated from the main project so they can later live in `nlp2cmd-benchmark`.

## Included benchmarks

- `llm_benchmark.py` — full LLM benchmark across local models and command domains
- `learning_benchmark.py` — evolutionary cache learning benchmark
- `thermodynamic_benchmark.py` — thermodynamic computing benchmark

## Run

```bash
PYTHONPATH=src python3 benchmarks/llm_benchmark.py
PYTHONPATH=src python3 benchmarks/learning_benchmark.py
PYTHONPATH=src python3 benchmarks/thermodynamic_benchmark.py
```

## Notes

- The lighter benchmark examples still live under `examples/02_benchmarks/`
- These scripts are the canonical benchmark entry points to extract into a separate repository later
