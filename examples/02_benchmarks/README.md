# Benchmarks - Performance Testing

This section contains lightweight examples for benchmarking and testing NLP2CMD performance.

For the canonical benchmark suite, see `./benchmarks/` at the repository root.

## Categories

### [performance_testing](./performance_testing/)
Comprehensive performance benchmarking for NLP2CMD operations.

### [sequential_testing](./sequential_testing/)
Sequential command processing benchmarks.

## Usage

Each benchmark generates detailed reports:

```bash
cd performance_testing
python benchmark.py

# Results will be saved to benchmark_report.json
```

## Metrics Measured

- Command processing latency
- Sequential processing performance
- Memory usage
- Throughput analysis
