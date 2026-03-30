# NLP2CMD Performance Benchmarking

This document explains how to benchmark NLP2CMD performance for single and sequential command processing.

## Overview

The NLP2CMD benchmarking tool measures:
- Single command processing latency
- Sequential command processing performance (10 commands)
- Throughput (commands per second)
- Performance across different adapters (Shell, SQL, Docker)

## Quick Start

### Run Benchmark with Make

```bash
# Generate a complete performance report
make report

# View the last benchmark report
make benchmark-view

# Clean benchmark reports
make benchmark-clean
```

### Run Benchmark Directly

```bash
# Run the main benchmark script
PYTHONPATH=src python3 benchmarks/llm_benchmark.py

# Run benchmark WITHOUT cache (forces fresh LLM calls for every query)
PYTHONPATH=src python3 benchmarks/llm_benchmark.py --no-cache

# Run the sequential commands example
python3 examples/02_benchmarks/sequential_testing/benchmark.py
```

### Benchmark Without Cache

For true LLM performance testing without cache influence:

```bash
# Standard benchmark (uses cache and template pipeline)
make benchmark

# Benchmark without cache (pure LLM performance)
PYTHONPATH=src python3 benchmarks/llm_benchmark.py --no-cache

# The --no-cache flag disables:
# - Cache lookups (exact, fuzzy, similarity)
# - Template pipeline (1615 patterns)
# Forces fresh LLM calls for every query
```

Use `--no-cache` when:
- Testing pure LLM accuracy without cache influence
- Measuring true LLM latency (not cached/template responses)
- Validating model improvements
- Avoiding cache hits from previous benchmark runs

## Understanding the Results

### Key Metrics

1. **Single Command Latency**: Average time to process one command (in milliseconds)
2. **Sequential Latency**: Average time per command when processing multiple commands sequentially
3. **Throughput**: Number of commands processed per second
4. **Total Time**: Total time to process all commands in sequence

### Performance Factors

- **Adapter Type**: Different adapters (Shell, SQL, Docker) have different performance characteristics
- **Command Complexity**: More complex commands take longer to process
- **System Load**: CPU and memory usage can affect performance
- **Warm-up Time**: First command may be slower due to initialization

## Example Results

Here's a sample benchmark output:

```
📊 Overall Performance:
  Average single command latency: 32.0ms
  Average sequential latency: 25.8ms
  Average throughput: 38.81 commands/sec

🏆 Top Performers:
  Fastest single command: docker adapter
  Fastest sequential: docker adapter
  Highest throughput: docker adapter

📈 Detailed Results by Adapter:

  SHELL:
    Single command: 29.9ms
    Sequential avg: 25.8ms
    Throughput: 38.67 cmd/s
    Total sequential time: 258.6ms
```

## Files Generated

1. **benchmark_report.json**: Detailed JSON report with all metrics
2. **benchmark_results.csv**: CSV file suitable for plotting in Excel or other tools
3. **sequential_benchmark_results.json**: Results from the sequential commands example

When using the canonical LLM benchmark (`benchmarks/llm_benchmark.py`), additional files are generated in `benchmark_output/`:

1. **benchmark_results.json**: Raw per-query results + aggregated accuracy stats
2. **benchmark_results.html**: Interactive charts
3. **benchmark_command_errors.md**: Auto-generated list of incorrect commands (`pattern_match=false` or `error`), grouped by model and domain

## Use Cases

### Performance Regression Testing

Run benchmarks after code changes to detect performance regressions:

```bash
# Before changes
make report
mv benchmark_report.json benchmark_before.json

# After changes
make report
mv benchmark_report.json benchmark_after.json

# Compare results
jq '.summary.average_single_command_latency_ms' benchmark_before.json benchmark_after.json
```

### System Capacity Planning

Use throughput metrics to determine system capacity:

- If throughput is 40 commands/sec, your system can handle:
  - 2,400 commands/minute
  - 144,000 commands/hour
  - 3.456 million commands/day

### Optimization Targets

Based on benchmark results, you can:
- Identify the fastest adapter for your use case
- Set performance targets for optimization
- Monitor performance over time

## Customizing Benchmarks

### Adding New Commands

Edit `benchmarks/llm_benchmark.py` for the canonical benchmark, or `examples/02_benchmarks/performance_testing/benchmark.py` for the lightweight adapter example, and modify the command lists:

```python
commands = {
    "shell": [
        "Your custom command 1",
        "Your custom command 2",
        # ... more commands
    ],
    # ... other adapters
}
```

### Testing Different Scenarios

Create custom benchmark scripts for specific use cases:

```python
# Example: Test file operations specifically
file_commands = [
    "Find all .log files",
    "Compress old logs",
    "Delete temporary files",
    # ... more file operations
]
```

## Troubleshooting

### High Latency

If you see high latency (>100ms per command):
1. Check system resources (CPU, memory)
2. Verify Python dependencies are properly installed
3. Consider running on a more powerful machine

### Inconsistent Results

For more consistent benchmarking:
1. Close other applications
2. Run multiple times and average the results
3. Use the same system configuration for comparisons

### Adapter Errors

If an adapter fails:
1. Check that all dependencies are installed
2. Verify the adapter configuration
3. Check logs for specific error messages

## Integrating with CI/CD

Add benchmarking to your CI pipeline:

```yaml
# .github/workflows/benchmark.yml
- name: Run Benchmark
  run: |
    python3 benchmarks/llm_benchmark.py
    
- name: Upload Results
  uses: actions/upload-artifact@v3
  with:
    name: benchmark-results
    path: |
      benchmark_report.json
      benchmark_results.csv
```

## Performance Tips

1. **Reuse Instances**: Create one NLP2CMD instance and reuse it for multiple commands
2. **Batch Processing**: Process commands in batches for better throughput
3. **Choose Right Adapter**: Use the adapter that best matches your domain
4. **Monitor Memory**: Large numbers of commands may require more memory

## Related Documentation

- [User Guide](../user-guide/user-guide.md) - Complete usage tutorial
- [API Documentation](../api/README.md) - Detailed API reference
- [Examples Guide](../reference/examples-guide.md) - Practical examples
