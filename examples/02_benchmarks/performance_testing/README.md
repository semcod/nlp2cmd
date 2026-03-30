# Performance Testing Benchmark

Lightweight performance benchmarking example for NLP2CMD.

For the canonical benchmark suite, see `benchmarks/` at the repository root.

## Overview

This benchmark tests:
- Single command processing latency
- Sequential command processing
- Performance across different adapters
- Memory usage and throughput

## Running the Benchmark

```bash
python benchmark.py
```

## Results

Results are saved to `benchmark_report.json` with detailed metrics including:
- Processing times
- Success rates
- Performance statistics
- Recommendations

## Customization

You can modify the benchmark to test:
- Different command sets
- Custom adapters
- Various input sizes
- Specific use cases
