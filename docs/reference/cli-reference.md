# CLI Reference Guide

This guide provides comprehensive documentation for the NLP2CMD Command Line Interface.

## 📚 Related Documentation

- **[Documentation Hub](../README.md)** - Entry point for all docs
- **[User Guide](../user-guide/user-guide.md)** - Complete usage tutorial
- **[Python API Guide](python-api.md)** - Programmatic usage
- **[API Reference](../api/README.md)** - Detailed API documentation
- **[Examples Guide](examples-guide.md)** - Examples overview

## Installation

```bash
pip install nlp2cmd
```

## Basic Syntax

The CLI uses the following syntax pattern:

```bash
nlp2cmd [OPTIONS] COMMAND [ARGS]
```

### Core Options

| Option | Short | Description |
| -------- | ------- | ------------- |
| `--query` | `-q` | Single query to process (required for text queries) |
| `--dsl` | `-d` | DSL type: auto, sql, shell, docker, kubernetes, dql |
| `--interactive` | `-i` | Start interactive mode |
| `--explain` | | Explain how the result was produced |
| `--auto-repair` | | Auto-apply repairs when possible |
| `--help` | `-h` | Show help message |

## Commands

### Main Query Processing

```bash
# Basic query (auto-detects DSL)
nlp2cmd --query "your natural language query"

# Specific DSL
nlp2cmd --dsl sql --query "show users from Warsaw"
nlp2cmd --dsl shell --query "find files larger than 100MB"
nlp2cmd --dsl docker --query "show all containers"
nlp2cmd --dsl kubernetes --query "scale nginx deployment"
nlp2cmd --dsl dql --query "find active users"
```

### Interactive Mode

```bash
# Start interactive REPL
nlp2cmd --interactive

# With specific DSL
nlp2cmd --interactive --dsl shell
```

### Environment Analysis

```bash
# Analyze system environment
nlp2cmd analyze-env

# Save to file
nlp2cmd analyze-env --output environment.json
```

### File Operations

```bash
# Validate configuration file
nlp2cmd validate config.json

# Repair file with backup
nlp2cmd repair docker-compose.yml --backup

# Validate without backup
nlp2cmd repair nginx.conf
```

## DSL Types

### SQL

```bash
nlp2cmd --dsl sql --query "show all users where city is Warsaw"
```

**Supported databases:**

- PostgreSQL
- MySQL
- SQLite

**Example outputs:**

```sql
SELECT * FROM users WHERE city = 'Warsaw';
SELECT COUNT(*) FROM orders WHERE created_at > '2024-01-01';
```

### Shell

```bash
nlp2cmd --dsl shell --query "find all log files larger than 10MB"
```

**Example outputs:**

```bash
find . -type f -name "*.log" -size +10MB -exec ls -lh {} \;
ps aux | grep nginx | head -10
df -h | grep -E "^/dev/"
```

### Docker

```bash
nlp2cmd --dsl docker --query "show all running containers"
```

**Example outputs:**

```bash
docker ps
docker ps -a
docker images
docker-compose up -d
```

### Kubernetes

```bash
nlp2cmd --dsl kubernetes --query "scale deployment nginx to 3 replicas"
```

**Example outputs:**

```bash
kubectl scale deployment nginx --replicas=3
kubectl get pods
kubectl apply -f deployment.yaml
```

### DQL (Doctrine)

```bash
nlp2cmd --dsl dql --query "find all active users"
```

**Example outputs:**

```php
SELECT u FROM User u WHERE u.active = true;
SELECT e FROM Employee e WHERE e.department.name = 'IT';
```

## Advanced Options

### Explain Mode

```bash
nlp2cmd --explain --query "check system status"
```

**Output includes:**

- Generated command
- Source (rules/llm)
- Domain classification
- Confidence score
- Latency information

### Auto-Repair Mode

```bash
nlp2cmd --auto-repair --query "fix nginx configuration"
```

**Features:**

- Automatic error detection
- Suggests fixes
- Applies repairs when safe

### Interactive Mode Features

In interactive mode, you can use special commands:

```bash
nlp2cmd> !env          # Show environment info
nlp2cmd> !tools        # List detected tools
nlp2cmd> !files        # List config files
nlp2cmd> !history      # Show command history
nlp2cmd> !clear        # Clear history
nlp2cmd> help          # Show help
nlp2cmd> exit          # Exit interactive mode
```

## Real-World Examples

### DevOps Workflow

```bash
# Check system status
nlp2cmd --query "check system health"

# Find and clean log files
nlp2cmd --dsl shell --query "find and delete log files older than 30 days"

# Docker operations
nlp2cmd --dsl docker --query "restart all containers with image nginx"

# Kubernetes scaling
nlp2cmd --dsl kubernetes --query "scale deployment based on CPU usage"
```

### Data Analysis

```bash
# Database queries
nlp2cmd --dsl sql --query "show top 10 customers by revenue"

# File analysis
nlp2cmd --dsl shell --query "count lines in all python files"

# Log analysis
nlp2cmd --dsl shell --query "find error patterns in access logs"
```

### System Administration

```bash
# Environment analysis
nlp2cmd analyze-env

# Configuration validation
nlp2cmd validate /etc/nginx/nginx.conf

# System monitoring
nlp2cmd --query "monitor disk space and alert if below 10%"
```

## Output Formats

### Standard Output

```bash
$ nlp2cmd --query "show users"
SELECT * FROM users;

📊 ⏱️  Time: 13.7ms | 💻 CPU: 0.0% | 🧠 RAM: 54.8MB (0.1%) | ⚡ Energy: 0.120mJ
```

### Explained Output

```bash
$ nlp2cmd --explain --query "show users"

# Unknown: sql/select
Source: rules
Domain: sql
Confidence: 0.95
Latency: 2.1ms

SELECT * FROM users;

📊 ⏱️  Time: 15.2ms | 💻 CPU: 0.0% | 🧠 RAM: 55.0MB (0.1%) | ⚡ Energy: 0.133mJ
```

### Interactive Output

```text
✅ Status: success
📊 Confidence: 100%

📝 Generated command:
╭──────────────────────────────────────────────────────────────────────────────╮
│ docker ps -a                                                                 │
╰──────────────────────────────────────────────────────────────────────────────╯

📊 ⏱️  Time: 2.2ms | 💻 CPU: 0.0% | 🧠 RAM: 55.2MB (0.1%) | ⚡ Energy: 0.019mJ
```

## Resource Metrics

Every command execution now displays comprehensive resource metrics:

### Metrics Displayed

| Metric | Description | Format |
| -------- | ------------- | -------- |
| **Time** | Execution time in milliseconds | `⏱️ Time: 13.7ms` |
| **CPU** | CPU usage percentage during execution | `💻 CPU: 0.0%` |
| **RAM** | Memory usage in MB and percentage | `🧠 RAM: 54.8MB (0.1%)` |
| **Energy** | Estimated energy consumption | `⚡ Energy: 0.120mJ` |

### Energy Units

- **mJ** (millijoules) for small consumption < 1J
- **J** (joules) for larger consumption ≥ 1J

### Example Outputs

```bash
# Fast DSL generation
$ nlp2cmd --dsl sql --query "show users"
SELECT * FROM users;
📊 ⏱️  Time: 2.2ms | 💻 CPU: 0.0% | 🧠 RAM: 55.2MB (0.1%) | ⚡ Energy: 0.019mJ

# Thermodynamic optimization
$ nlp2cmd --query "optimize resource allocation"
[Optimization solution...]
📊 ⏱️  Time: 1125.7ms | 💻 CPU: 0.0% | 🧠 RAM: 59.3MB (0.1%) | ⚡ Energy: 0.011J
```

### Performance Characteristics

- **DSL Generation**: Typically 2-20ms, low energy consumption
- **Thermodynamic Optimization**: 100-2000ms, higher energy usage
- **Memory**: Baseline ~55MB + small increases for complex operations
- **CPU**: Usually minimal on modern systems

## Error Handling

### Common Errors

#### 1. Missing --query flag

```bash
❌ nlp2cmd "show users"
✅ nlp2cmd --query "show users"
```

#### 2. Invalid DSL

```bash
❌ nlp2cmd --dsl invalid --query "show users"
✅ nlp2cmd --dsl sql --query "show users"
```

#### 3. File not found

```bash
❌ nlp2cmd validate nonexistent.json
✅ nlp2cmd validate existing-config.json
```

### Troubleshooting

1. **Check installation**: `pip show nlp2cmd`
2. **Verify syntax**: Use `--help` to see correct options
3. **Enable verbose mode**: Use `--explain` for detailed output
4. **Check environment**: Run `nlp2cmd analyze-env`

## Integration Examples

### Shell Scripts

```bash
#!/bin/bash
# Automated system check

echo "Checking system health..."
nlp2cmd --query "check system health" > health_report.txt

echo "Analyzing logs..."
nlp2cmd --dsl shell --query "find recent errors in logs" >> health_report.txt

echo "Checking Docker status..."
nlp2cmd --dsl docker --query "show container status" >> health_report.txt
```

### Cron Jobs

```bash
# Daily system maintenance
0 2 * * * /usr/local/bin/nlp2cmd --query "cleanup temporary files"
0 3 * * 0 /usr/local/bin/nlp2cmd analyze-env --output /var/log/system_analysis.json
```

### CI/CD Pipeline

```bash
# GitHub Actions example
- name: Analyze environment
  run: nlp2cmd analyze-env --output env_analysis.json

- name: Validate configurations
  run: |
    nlp2cmd validate docker-compose.yml
    nlp2cmd validate k8s/deployment.yaml
```

## Performance Tips

1. **Use specific DSL**: `--dsl sql` is faster than auto-detection
2. **Batch queries**: Use interactive mode for multiple queries
3. **Cache results**: Environment analysis can be saved and reused
4. **Optimize queries**: Be specific in your natural language queries

## See Also

- [Python API Guide](../reference/python-api.md) - Programmatic usage
- [Examples Guide](../reference/examples-guide.md) - Comprehensive examples
- [User Guide](../user-guide/user-guide.md) - Complete tutorial
