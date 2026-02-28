# Advanced Flow Analyzer

Comprehensive system behavior analysis tool combining static and dynamic analysis for reverse engineering and understanding complex codebases.

## Features

### 🔍 **Multi-Mode Analysis**
- **Static**: AST-based control flow and data flow analysis
- **Dynamic**: Runtime execution tracing
- **Hybrid**: Combined static + dynamic for maximum insight
- **Behavioral**: Pattern extraction and recognition
- **Reverse**: LLM-ready outputs for system reconstruction

### 📊 **Analysis Capabilities**
- Control Flow Graph (CFG) generation
- Data Flow Graph (DFG) tracking
- Call graph reconstruction
- Variable dependency mapping
- State machine detection
- Behavioral pattern extraction
- Recursive pattern identification

### 🎯 **Pattern Recognition**
- Sequential execution patterns
- Conditional branching patterns
- Iterative/loop patterns
- Recursive function patterns
- State machine patterns

### 📁 **Output Formats**
- **LLM Prompt**: System analysis in natural language
- **YAML**: Structured data for programmatic processing
- **Mermaid**: Flow diagrams for documentation
- **PNG**: Visual flow representations
- **JSON**: Raw diagram data
- **Report**: Summary statistics and insights

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Basic Analysis
```bash
python flow.py /path/to/project
```

### Analysis Modes
```bash
# Static analysis only (fastest)
python flow.py /path/to/project -m static

# Dynamic analysis with tracing
python flow.py /path/to/project -m dynamic

# Hybrid analysis (recommended)
python flow.py /path/to/project -m hybrid

# Behavioral pattern focus
python flow.py /path/to/project -m behavioral

# Reverse engineering ready
python flow.py /path/to/project -m reverse
```

### Custom Output
```bash
python flow.py /path/to/project -o my_analysis
```

## Output Files

| File | Description |
|------|-------------|
| `system_analysis_prompt.md` | Complete system description for LLM |
| `system_analysis.yaml` | Structured analysis data |
| `system_flow.mmd` | Mermaid diagram source |
| `system_flow.png` | Flow visualization |
| `diagram_data.json` | Raw graph data |
| `analysis_report.md` | Summary and statistics |

## Understanding the Output

### LLM Prompt Structure
The generated prompt includes:
- System overview with metrics
- Call graph structure
- Behavioral patterns with confidence scores
- Data flow insights
- State machine definitions
- Reverse engineering guidelines

### Behavioral Patterns
Each pattern includes:
- **Name**: Descriptive identifier
- **Type**: sequential, conditional, iterative, recursive, state_machine
- **Entry/Exit points**: Key functions
- **Decision points**: Conditional logic locations
- **Data transformations**: Variable dependencies
- **Confidence**: Pattern detection certainty

### Reverse Engineering Guidelines
The analysis provides specific guidance for:
1. Preserving call graph structure
2. Implementing identified patterns
3. Maintaining data dependencies
4. Recreating state machines
5. Preserving decision logic

## Advanced Features

### State Machine Detection
Automatically identifies:
- State variables
- Transition methods
- Source and destination states
- State machine hierarchy

### Data Flow Tracking
Maps:
- Variable dependencies
- Data transformations
- Information flow paths
- Side effects

### Dynamic Tracing
When using dynamic mode:
- Function entry/exit timing
- Call stack reconstruction
- Exception tracking
- Performance profiling

## Integration with LLMs

The generated `system_analysis_prompt.md` is designed to be:
- **Comprehensive**: Contains all necessary system information
- **Structured**: Organized for easy parsing
- **Actionable**: Includes specific implementation guidance
- **Language-agnostic**: Describes behavior, not implementation

Example usage with an LLM:
```
"Based on the system analysis provided, implement this system in Go,
preserving all behavioral patterns and data flow characteristics."
```

## Limitations

- Dynamic analysis requires test files
- Complex inheritance hierarchies may need manual review
- External library calls are treated as black boxes
- Runtime reflection and metaprogramming not fully captured

## Contributing

The analyzer is designed to be extensible. Key areas for enhancement:
- Additional pattern types
- Language-specific optimizations
- Improved visualization
- Real-time analysis mode

## License

This tool is part of the STTS project and follows the same license terms.
