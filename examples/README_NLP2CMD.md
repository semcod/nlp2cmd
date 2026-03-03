# NLP2CMD Examples with Direct nlp2cmd Usage

This directory contains equivalent scripts that use nlp2cmd directly instead of the lower-level APIs. Each example demonstrates how to accomplish the same tasks using natural language commands processed by nlp2cmd.

## Quick Start

### Using the Bash Runner (Recommended)

The `run_examples.sh` script provides an easy way to run all examples:

```bash
# List all available examples
./run_examples.sh --list

# Run basic shell commands example
./run_examples.sh 01_basics shell_fundamentals --verbose

# Run drawing example with headless mode
./run_examples.sh 09_online_drawing 01_draw_chat_shapes --headless

# Run code editor example
./run_examples.sh 10_online_code_editors 01_codepen_live --verbose
```

### Running Individual Scripts

You can also run each script directly:

```bash
# Basic examples
python3 01_basics/shell_fundamentals/01_basics_shell_nlp2cmd.py --command "list files" --verbose
python3 01_basics/docker_basics/01_basics_docker_nlp2cmd.py --command "show images" --verbose

# Online drawing
python3 09_online_drawing/01_draw_chat_shapes_nlp2cmd.py --shape house --color blue --headless
python3 09_online_drawing/03_adaptive_drawing_nlp2cmd.py --prompt "Draw a colorful mandala" --verbose

# Online code editors
python3 10_online_code_editors/01_codepen_live_nlp2cmd.py --preset hello --headless
python3 10_online_code_editors/02_mycompiler_run_nlp2cmd.py --code fibonacci --lang python --verbose
python3 10_online_code_editors/03_adaptive_code_nlp2cmd.py --prompt "Write a sorting algorithm" --headless
python3 10_online_code_editors/04_jsfiddle_frontend_nlp2cmd.py --preset calculator --verbose
python3 10_online_code_editors/05_dynamic_executor_nlp2cmd.py --prompt "Calculate prime numbers" --headless

# API key management
python3 08_api_key_management/01_diagnose_credentials_nlp2cmd.py --service openrouter --verbose
```

## Available Examples

### 📁 01_basics - Basic Commands

**shell_fundamentals**
- Demonstrates basic shell command automation
- Commands: list files, system info, processes, disk usage, memory, network
- Script: `01_basics_shell_nlp2cmd.py`

**docker_basics**
- Demonstrates Docker command automation
- Commands: list containers, show images, system info, cleanup, logs
- Script: `01_basics_docker_nlp2cmd.py`

### 🎨 09_online_drawing - Drawing Automation

**01_draw_chat_shapes**
- Draw geometric shapes on online whiteboards (draw.chat with fallback to jspaint.app)
- Shapes: house, star, circle, rectangle, line, spiral, heart, flower, triangle, ellipse
- Colors: any color name or hex value
- Features: coordinate scaling, automatic fallback, color declensions
- Script: `01_draw_chat_shapes_nlp2cmd.py`

**03_adaptive_drawing**
- LLM-guided drawing with adaptive routing and vision verification
- Natural language prompts for complex drawings
- Automatic error detection and retry with fallback mechanisms
- Based on analysis findings: coordinate scaling, color handling, site discovery
- Script: `03_adaptive_drawing_nlp2cmd.py`

**Analysis-Based Features:**
- **Coordinate Scaling**: Automatic scaling for different canvas sizes
- **Color Handling**: Full support on jspaint.app (28-color palette), limited on kleki.com
- **Site Discovery**: Automatic fallback from draw.chat → jspaint.app → kleki.com
- **Polish Declensions**: Proper accusative forms (czerwoną, niebieską, etc.)
- **Popup Dismissal**: Cookie banners, GDPR notices, login modals
- **Canvas Polling**: Dynamic wait up to 10s for slow-loading sites

**04_object_database**
- Multi-object drawing with external database integration
- Text-to-2DObject generation via LLM fallback for unknown shapes
- Autonomous database fetching from HuggingFace, GitHub, FontAwesome
- Scene composition with automatic layout
- Local cache with TTL for offline operation
- Script: `04_object_database_drawing.py`

**Object Databases:**
- **HuggingFace**: shapenet, geometric datasets
- **GitHub**: geometric-shapes-db repository
- **FontAwesome**: Icon shapes (star, heart, cloud, etc.)
- **Built-in**: 7 basic shapes as fallback
- **LLM Generated**: Dynamic shape generation for any description

**Usage:**
```bash
# Show available databases
python3 04_object_database_drawing.py --show-database
./run_examples.sh 09_online_drawing 04_object_database --show-database

# Draw scene with multiple objects
python3 04_object_database_drawing.py --objects "tree,house,sun,car,cloud"
./run_examples.sh 09_online_drawing 04_object_database --objects "tree,house,sun"

# Use natural language scene description
python3 04_object_database_drawing.py --scene "forest with trees and a house"

# Disable LLM fallback (use only built-in + cached shapes)
python3 04_object_database_drawing.py --objects "car,tree" --no-llm-fallback
```

### 💻 10_online_code_editors - Code Editor Automation

**01_codepen_live**
- Write HTML/CSS/JS on CodePen with live preview
- Presets: hello, animated_gradient, clock, todo
- Script: `01_codepen_live_nlp2cmd.py`

**02_mycompiler_run**
- Run code on myCompiler.io
- Languages: Python, JavaScript, C++
- Presets: fibonacci, factorial, sorting, hello
- Script: `02_mycompiler_run_nlp2cmd.py`

**03_adaptive_code**
- LLM-guided code generation with adaptive routing
- Natural language prompts for code generation
- Automatic error detection and repair
- Script: `03_adaptive_code_nlp2cmd.py`

**04_jsfiddle_frontend**
- Write frontend code on JSFiddle
- Presets: hello, particles, calculator
- Script: `04_jsfiddle_frontend_nlp2cmd.py`

**05_dynamic_executor**
- Dynamic code execution using nlp2cmd orchestration
- Natural language to code generation and execution
- LLM-driven planning and execution
- Script: `05_dynamic_executor_nlp2cmd.py`

### 🔑 08_api_key_management - Credential Management

**01_diagnose_credentials**
- Diagnose and extract API credentials from various services
- Services: OpenRouter, Anthropic, OpenAI, GitHub
- Script: `01_diagnose_credentials_nlp2cmd.py`

## Command Line Options

All scripts support these common options:

- `--verbose` - Show detailed nlp2cmd processing information
- `--headless` - Run browser automation in headless mode (browser examples)
- `--help` - Show script-specific help

## Environment Setup

1. Ensure you have Python 3.8+ installed
2. Install nlp2cmd dependencies:
   ```bash
   cd /path/to/nlp2cmd
   pip install -e .
   ```
3. For browser examples, install Playwright browsers:
   ```bash
   playwright install chromium
   ```

## Natural Language Commands

The examples demonstrate various natural language patterns:

### Polish Commands (Primary)
- "Pokaż pliki w bieżącym katalogu" - Show files in current directory
- "Otwórz draw.chat i narysuj dom w kolorze niebieskim" - Open draw.chat and draw a blue house
- "Otwórz codepen.io i stwórz stronę z przyciskiem" - Open codepen.io and create a page with a button

### English Commands (Secondary)
- "Show system information" - Display system info
- "Open draw.chat and draw a star in red color" - Draw on whiteboard
- "Write a Python program for fibonacci numbers" - Code generation

## Error Handling

The scripts include comprehensive error handling:

- Automatic retry on failures
- Graceful fallbacks for missing dependencies
- Clear error messages and suggestions
- Verbose logging for debugging

## Comparison with Original Examples

| Original | nlp2cmd Equivalent | Key Differences |
|----------|-------------------|-----------------|
| Direct API usage | Natural language commands | Higher-level abstraction |
| Manual browser control | Automated orchestration | Less boilerplate code |
| Hardcoded patterns | LLM-driven generation | More flexible |
| Complex setup | Simple CLI interface | Easier to use |

## Troubleshooting

### Common Issues

1. **Module not found errors**
   ```bash
   export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
   ```

2. **Playwright browser not installed**
   ```bash
   playwright install chromium
   ```

3. **Permission denied on run_examples.sh**
   ```bash
   chmod +x run_examples.sh
   ```

4. **nlp2cmd command not found**
   - Ensure you're in the project root directory
   - Check that src/nlp2cmd exists
   - Install the package in development mode

### Getting Help

```bash
# Show all available examples
./run_examples.sh --list

# Show usage information
./run_examples.sh --help

# Run with verbose logging for debugging
./run_examples.sh 01_basics shell_fundamentals --verbose
```

## Contributing

To add new examples:

1. Create a new script following the existing pattern
2. Use the `nlp2cmd.cli.main` module for command execution
3. Add appropriate command-line arguments
4. Update this README and `run_examples.sh`
5. Test with `--verbose` flag for debugging

The key pattern is:
```python
from nlp2cmd.cli.main import main as nlp2cmd_main

async def run_nlp2cmd_command(command: str, **kwargs):
    # Build nlp2cmd arguments
    args = ["--run", command] + additional_args
    sys.argv = ["nlp2cmd"] + args
    await nlp2cmd_main()
```
