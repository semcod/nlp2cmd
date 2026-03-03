#!/bin/bash
# run_examples.sh - Bash script to run nlp2cmd examples
# Usage: ./run_examples.sh [example_name] [options]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Base directory
EXAMPLES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$EXAMPLES_DIR")"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Python script exists
check_script() {
    local script_path="$1"
    if [[ ! -f "$script_path" ]]; then
        print_error "Script not found: $script_path"
        return 1
    fi
}

# Function to run Python script
run_python_script() {
    local script_path="$1"
    shift
    local args="$@"
    
    print_status "Running: $(basename "$script_path") $args"
    print_status "Path: $script_path"
    echo
    
    cd "$(dirname "$script_path")"
    python3 "$(basename "$script_path")" $args
    
    local exit_code=$?
    echo
    if [[ $exit_code -eq 0 ]]; then
        print_success "Script completed successfully"
    else
        print_error "Script failed with exit code $exit_code"
    fi
    echo
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [example_category] [example_name] [options]"
    echo
    echo "Available categories:"
    echo "  01_basics           - Basic examples"
    echo "  09_online_drawing   - Online drawing automation"
    echo "  10_online_code_editors - Online code editor automation"
    echo "  08_api_key_management - API key management"
    echo
    echo "Available examples:"
    echo "  shell_fundamentals  - Basic shell commands"
    echo "  docker_basics       - Basic Docker commands"
    echo "  01_draw_chat_shapes - Draw shapes on draw.chat"
    echo "  03_adaptive_drawing - Adaptive drawing with LLM"
    echo "  01_codepen_live     - Write code on CodePen"
    echo "  02_mycompiler_run   - Run code on myCompiler.io"
    echo "  03_adaptive_code    - Adaptive code generation"
    echo "  04_jsfiddle_frontend - Frontend code on JSFiddle"
    echo "  05_dynamic_executor - Dynamic code execution"
    echo "  01_diagnose_credentials - Credential diagnosis"
    echo
    echo "Options:"
    echo "  --headless          - Run in headless mode (browser examples)"
    echo "  --verbose           - Show verbose output"
    echo "  --help              - Show this help message"
    echo
    echo "Examples:"
    echo "  $0 01_basics shell_fundamentals --verbose"
    echo "  $0 09_online_drawing 01_draw_chat_shapes --headless"
    echo "  $0 10_online_code_editors 01_codepen_live --verbose"
}

# Function to run specific example
run_example() {
    local category="$1"
    local example="$2"
    shift 2
    local args="$@"
    
    local script_path=""
    
    case "$category" in
        "01_basics")
            case "$example" in
                "shell_fundamentals")
                    script_path="$EXAMPLES_DIR/01_basics/shell_fundamentals/01_basics_shell_nlp2cmd.py"
                    ;;
                "docker_basics")
                    script_path="$EXAMPLES_DIR/01_basics/docker_basics/01_basics_docker_nlp2cmd.py"
                    ;;
                *)
                    print_error "Unknown example: $example"
                    return 1
                    ;;
            esac
            ;;
        "09_online_drawing")
            case "$example" in
                "01_draw_chat"|"01_draw_chat_shapes")
                    script_path="$EXAMPLES_DIR/09_online_drawing/01_draw_chat/run.py"
                    ;;
                "02_picsart"|"02_picsart_painting")
                    script_path="$EXAMPLES_DIR/09_online_drawing/02_picsart/run.py"
                    ;;
                "03_adaptive"|"03_adaptive_drawing")
                    script_path="$EXAMPLES_DIR/09_online_drawing/03_adaptive/run.py"
                    ;;
                "04_object_database"|"04_database_drawing")
                    script_path="$EXAMPLES_DIR/09_online_drawing/04_object_database/run.py"
                    ;;
                "05_autonomous"|"05_autonomous_drawing")
                    script_path="$EXAMPLES_DIR/09_online_drawing/05_autonomous/run.py"
                    ;;
                "06_visual_validator"|"06_validator")
                    script_path="$EXAMPLES_DIR/09_online_drawing/06_visual_validator/run.py"
                    ;;
                "07_shape_gallery"|"07_gallery")
                    script_path="$EXAMPLES_DIR/09_online_drawing/07_shape_gallery/run.py"
                    ;;
                "08_search_demo"|"08_search"|"search")
                    script_path="$EXAMPLES_DIR/09_online_drawing/08_search_demo/run.py"
                    ;;
                *)
                    print_error "Unknown example: $example"
                    return 1
                    ;;
            esac
            ;;
        "10_online_code_editors")
            case "$example" in
                "01_codepen_live")
                    script_path="$EXAMPLES_DIR/10_online_code_editors/01_codepen_live_nlp2cmd.py"
                    ;;
                "02_mycompiler_run")
                    script_path="$EXAMPLES_DIR/10_online_code_editors/02_mycompiler_run_nlp2cmd.py"
                    ;;
                "03_adaptive_code")
                    script_path="$EXAMPLES_DIR/10_online_code_editors/03_adaptive_code_nlp2cmd.py"
                    ;;
                "04_jsfiddle_frontend")
                    script_path="$EXAMPLES_DIR/10_online_code_editors/04_jsfiddle_frontend_nlp2cmd.py"
                    ;;
                "05_dynamic_executor")
                    script_path="$EXAMPLES_DIR/10_online_code_editors/05_dynamic_executor_nlp2cmd.py"
                    ;;
                *)
                    print_error "Unknown example: $example"
                    return 1
                    ;;
            esac
            ;;
        "08_api_key_management")
            case "$example" in
                "01_diagnose_credentials")
                    script_path="$EXAMPLES_DIR/08_api_key_management/01_diagnose_credentials_nlp2cmd.py"
                    ;;
                *)
                    print_error "Unknown example: $example"
                    return 1
                    ;;
            esac
            ;;
        *)
            print_error "Unknown category: $category"
            return 1
            ;;
    esac
    
    if check_script "$script_path"; then
        run_python_script "$script_path" $args
    fi
}

# Function to list all available examples
list_examples() {
    print_status "Available nlp2cmd examples:"
    echo
    echo "📁 01_basics/"
    echo "  ├── shell_fundamentals - Basic shell commands"
    echo "  └── docker_basics      - Basic Docker commands"
    echo
    echo "🎨 09_online_drawing/"
    echo "  ├── 01_draw_chat_shapes   - Draw shapes on draw.chat"
    echo "  ├── 02_picsart_painting   - Paint patterns on Picsart"
    echo "  ├── 03_adaptive_drawing   - Adaptive drawing with LLM"
    echo "  ├── 04_object_database    - Database + LLM object generation"
    echo "  ├── 05_autonomous_drawing - Full pipeline: fetch→draw→validate→correct"
    echo "  ├── 06_visual_validator   - Vision LLM drawing verification"
    echo "  ├── 07_shape_gallery      - Preview all 33+ built-in shapes"
    echo "  └── 08_search_demo        - Open source internet search"
    echo
    echo "💻 10_online_code_editors/"
    echo "  ├── 01_codepen_live        - Write code on CodePen"
    echo "  ├── 02_mycompiler_run      - Run code on myCompiler.io"
    echo "  ├── 03_adaptive_code       - Adaptive code generation"
    echo "  ├── 04_jsfiddle_frontend   - Frontend code on JSFiddle"
    echo "  └── 05_dynamic_executor    - Dynamic code execution"
    echo
    echo "🔑 08_api_key_management/"
    echo "  └── 01_diagnose_credentials - Credential diagnosis"
    echo
    echo "Usage: $0 [category] [example] [options]"
}

# Main script logic
main() {
    # Check for help flag
    if [[ "$1" == "--help" || "$1" == "-h" ]]; then
        show_usage
        exit 0
    fi
    
    # Check for list flag
    if [[ "$1" == "--list" || "$1" == "-l" ]]; then
        list_examples
        exit 0
    fi
    
    # Check if we have enough arguments
    if [[ $# -lt 2 ]]; then
        print_error "Insufficient arguments"
        echo
        show_usage
        exit 1
    fi
    
    local category="$1"
    local example="$2"
    shift 2
    
    print_status "NLP2CMD Examples Runner"
    print_status "Project root: $PROJECT_ROOT"
    print_status "Examples directory: $EXAMPLES_DIR"
    echo
    
    # Check if we're in the right directory
    if [[ ! -d "$PROJECT_ROOT/src" ]]; then
        print_error "Not in a valid nlp2cmd project directory"
        print_error "Expected to find: $PROJECT_ROOT/src"
        exit 1
    fi
    
    # Check if nlp2cmd is available
    if ! python3 -c "import nlp2cmd" 2>/dev/null; then
        print_warning "nlp2cmd module not found in Python path"
        print_status "Attempting to use local src directory..."
        export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"
    fi
    
    # Run the example
    run_example "$category" "$example" "$@"
}

# Run main function with all arguments
main "$@"
