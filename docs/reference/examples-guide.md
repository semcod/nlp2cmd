# Examples Guide

This guide provides a comprehensive overview of all NLP2CMD examples, organized by category and complexity.

## 📚 Related Documentation

- **[Documentation Hub](../README.md)** - Entry point for all docs
- **[User Guide](../user-guide/user-guide.md)** - Complete usage tutorial
- **[API Reference](../api/README.md)** - Detailed API documentation
- **[Python API Guide](python-api.md)** - Programmatic usage

## 🗂️ Examples Structure

```text
examples/
├── 01_basics/                     # Fundamental examples and getting started
│   ├── app2schema/               # AppSpec generation from applications
│   ├── docker_basics/            # Docker command examples
│   └── kubernetes_basics/        # Kubernetes basics
├── 02_benchmarks/                # Performance testing and benchmarking
│   ├── performance_testing/      # Performance measurement tools
│   └── sequential_testing/       # Sequential test execution
├── 03_integrations/              # Integration with external systems
│   ├── pipelines/                # Pipeline integrations
│   ├── toon_format/              # Toon format examples
│   └── validation/               # Validation integrations
├── 04_domain_specific/           # Domain-specific use cases
│   ├── bioinformatics/           # Bioinformatics workflows
│   ├── data_science/             # Data science examples
│   ├── debugging/                # Debugging workflows
│   └── [10 more domains...]      # Various specialized domains
├── 05_advanced_features/         # Advanced features and experimental
│   ├── thermodynamic/            # Thermodynamic optimization
│   └── [other features...]       # Advanced capabilities
├── 06_desktop_automation/        # Desktop GUI automation
│   ├── 04_browser_tabs/          # Browser tab management
│   ├── 05_email_client/          # Email automation
│   ├── 06_env_extract/           # API key extraction
│   ├── 07_canvas_drawing/        # Canvas drawing automation
│   ├── 08_captcha_solver/        # CAPTCHA solving
│   └── 09_complex_commands/      # Complex command planning
├── 07_browser_automation/        # Browser automation examples
│   └── [browser examples...]     # Web automation workflows
├── 08_api_key_management/        # API key management tools
│   └── [key management...]       # Secure key handling
├── 09_online_drawing/            # Online drawing automation
│   ├── 01_draw_chat/             # Draw.chat automation
│   ├── 02_picsart/               # Picsart drawing
│   ├── 03_adaptive/              # Adaptive drawing
│   ├── 04_object_database/       # Object database usage
│   ├── 05_autonomous/            # Autonomous drawing
│   ├── 06_visual_validator/      # Visual validation
│   ├── 07_shape_gallery/         # Shape gallery demo
│   └── [more drawing examples...] # Advanced drawing features
├── 10_online_code_editors/       # Online code editor automation
│   ├── 01_codepen_live/          # CodePen automation
│   ├── 02_mycompiler_run/        # MyCompiler.io automation
│   ├── 03_adaptive_code/         # Adaptive code generation
│   ├── 04_jsfiddle_frontend/     # JSFiddle automation
│   └── 05_dynamic_executor/      # Dynamic code execution
├── _dynamic_orchestrator.py      # Dynamic orchestrator demo
├── run_examples.sh               # Script to run all examples
└── README.md                     # This file
```

## 🚀 Quick Start Examples

### 1. Basics - Getting Started

**Location:** `examples/01_basics/`

```bash
# AppSpec generation
cd examples/01_basics/app2schema
python appspec_demo.py

# Docker basics
cd examples/01_basics/docker_basics
python docker_demo.py

# Kubernetes basics
cd examples/01_basics/kubernetes_basics
python k8s_demo.py
```

**What you'll learn:**
- Basic NLP2CMD concepts
- AppSpec file generation
- Docker command generation
- Kubernetes resource management

### 2. Desktop Automation

**Location:** `examples/06_desktop_automation/`

```bash
# Browser tab management
cd examples/06_desktop_automation/04_browser_tabs
bash run.sh

# Canvas drawing
cd examples/06_desktop_automation/07_canvas_drawing
python canvas_demo.py

# Complex command planning
cd examples/06_desktop_automation/09_complex_commands
python complex_planner.py
```

**What you'll learn:**
- Desktop GUI automation
- Browser automation
- Canvas drawing techniques
- Complex command planning

### 3. Online Drawing

**Location:** `examples/09_online_drawing/`

```bash
# Run all drawing examples
cd examples/09_online_drawing
./run.sh

# Individual examples
./run.sh 01_draw_chat
./run.sh 02_picsart
./run.sh 03_adaptive
```

**What you'll learn:**
- Web-based drawing automation
- Shape recognition and generation
- Visual validation
- Autonomous drawing workflows

### 4. Online Code Editors

**Location:** `examples/10_online_code_editors/`

```bash
# CodePen automation
cd examples/10_online_code_editors/01_codepen_live
python run.py

# Dynamic code execution
cd examples/10_online_code_editors/05_dynamic_executor
python run.py --prompt "Write fibonacci in python"
```

**What you'll learn:**
- Online code editor automation
- Dynamic code generation
- Code injection techniques
- Output validation

### 5. Dynamic Orchestrator

**File:** `examples/_dynamic_orchestrator.py`

```bash
python examples/_dynamic_orchestrator.py --prompt "Create a dashboard with charts"
```

**What you'll learn:**
- LLM-driven orchestration
- Multi-step task planning
- Error recovery and repair
- Dynamic code generation

## 📊 Performance Benchmarks

**Location:** `examples/02_benchmarks/`

```bash
# Run performance tests
cd examples/02_benchmarks/performance_testing
python benchmark.py

# Sequential testing
cd examples/02_benchmarks/sequential_testing
python run_sequential.py
```

## 🔧 Domain-Specific Examples

**Location:** `examples/04_domain_specific/`

Available domains:
- **Bioinformatics** - DNA sequence analysis, protein folding
- **Data Science** - Data processing, ML pipelines
- **Debugging** - Code debugging workflows
- **Finance** - Trading algorithms, risk analysis
- **Healthcare** - Medical data processing
- **Smart Cities** - Urban management systems
- And many more...

## 🎯 Running Examples

### Prerequisites

1. Install NLP2CMD:
```bash
pip install nlp2cmd
```

2. Configure environment:
```bash
export NLP2CMD_MODEL="ollama/qwen2.5:7b"
export NLP2CMD_API_BASE="http://localhost:11434"
```

### Running Individual Examples

```bash
# Navigate to example directory
cd examples/[category]/[specific_example]

# Run the example
python example.py

# Or use the run script
./run.sh
```

### Running All Examples

```bash
# Run all examples with the master script
cd examples
./run_examples.sh

# Run specific category
./run_examples.sh --category 09_online_drawing

# Run with specific options
./run_examples.sh --headless --verbose
```

## 🛠️ Configuration

Most examples support configuration via:

1. **Command line arguments:**
```bash
python example.py --model gpt-4 --headless --verbose
```

2. **Environment variables:**
```bash
export NLP2CMD_MODEL="gpt-4"
export NLP2CMD_HEADLESS="true"
export NLP2CMD_VERBOSE="true"
```

3. **Configuration files:**
```yaml
# config.yaml
model: "gpt-4"
headless: true
verbose: true
timeout: 30000
```

## 📝 Example Categories Explained

### 01_basics
Fundamental examples for beginners. Learn the core concepts of NLP2CMD.

### 02_benchmarks
Performance measurement and testing tools. Evaluate system performance.

### 03_integrations
Integration examples with external systems and APIs.

### 04_domain_specific
Specialized examples for specific domains and industries.

### 05_advanced_features
Advanced and experimental features. Cutting-edge capabilities.

### 06_desktop_automation
Desktop GUI automation examples. Automate desktop applications.

### 07_browser_automation
Browser automation examples. Web scraping and automation.

### 08_api_key_management
Tools for managing API keys and credentials securely.

### 09_online_drawing
Online drawing automation. Create art on web-based drawing tools.

### 10_online_code_editors
Online code editor automation. Write and execute code in web editors.

## 🔍 Troubleshooting

### Common Issues

1. **Model not available:**
```bash
# Pull the model
ollama pull qwen2.5:7b
```

2. **Permission denied:**
```bash
# Make scripts executable
chmod +x examples/**/*.sh
```

3. **Missing dependencies:**
```bash
# Install additional dependencies
pip install playwright
playwright install chromium
```

### Getting Help

- Check individual example READMEs
- Review the main documentation
- Open an issue on GitHub

## 🚀 Next Steps

1. Start with basics in `01_basics/`
2. Explore your domain in `04_domain_specific/`
3. Try advanced features in `05_advanced_features/`
4. Build your own examples using the patterns shown

## 📚 Additional Resources

- **[Architecture Guide](../architecture/)** - System architecture
- **[Thermodynamic Integration](../../THERMODYNAMIC_INTEGRATION.md)** - Advanced optimization
- **[Contributing Guide](../../CONTRIBUTING.md)** - Development guidelines
