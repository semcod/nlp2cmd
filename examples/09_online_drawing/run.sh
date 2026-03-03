#!/bin/bash
#
# Unified launcher for NLP2CMD Examples - VISIBLE MODE (see browser automation!)
# 
# Usage:
#   ./run.sh list                    # List all available examples
#   ./run.sh 01_draw_chat            # Run specific example (VISIBLE by default)
#   ./run.sh draw "red star"         # Quick draw command (VISIBLE)
#   ./run.sh autonomous "blue cat"   # Run autonomous pipeline (VISIBLE)
#
# Options:
#   --headless    Run browser in background (hidden)
#   -v            Verbose output
#   --help        Show help

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Help function
show_help() {
    cat << EOF
NLP2CMD Examples Launcher - VISIBLE MODE (browser window shown by default!)

Usage:
  $(basename "$0") list                          List all examples
  $(basename "$0") <example_id> [args...]        Run specific example
  $(basename "$0") draw "<description>"          Quick draw command
  $(basename "$0") autonomous "<description>"      Run autonomous pipeline

Examples:
  $(basename "$0") 01_draw_chat                  # Draw house (VISIBLE)
  $(basename "$0") 03_adaptive --query "star"    # Adaptive drawing (VISIBLE)
  $(basename "$0") draw "red star"               # Quick draw (VISIBLE)
  $(basename "$0") autonomous "cat and fish"     # Full pipeline (VISIBLE)
  $(basename "$0") draw "blue house" --headless   # Run hidden

Options (passed to examples):
  --headless      Run browser in background (hidden mode)
  -v, --verbose   Show detailed logs

Available Examples:
  01_draw_chat         - Draw shapes on draw.chat whiteboard
  02_picsart           - Paint on Picsart/Kleki
  03_adaptive          - LLM-guided adaptive drawing
  04_object_database   - Multi-object from online DB
  05_autonomous        - Full autonomous pipeline
  06_visual_validator  - Vision-based validation
  07_shape_gallery     - Browse all shapes

For more info: nlp2cmd examples --help

💡 TIP: Browser runs in VISIBLE mode by default so you can see the magic happen!
    Use --headless only if you want to run in background.
EOF
}

# Check if nlp2cmd is available
check_nlp2cmd() {
    if ! command -v nlp2cmd &> /dev/null; then
        # Try to find it in the repo
        if [ -f "$SCRIPT_DIR/../../src/nlp2cmd/__main__.py" ]; then
            Nlp2cmd() { python3 -m nlp2cmd "$@"; }
        else
            echo -e "${RED}Error: nlp2cmd not found${NC}"
            echo "Please install: pip install -e ."
            exit 1
        fi
    else
        Nlp2cmd() { nlp2cmd "$@"; }
    fi
}

# Main function
main() {
    if [ $# -eq 0 ] || [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
        show_help
        exit 0
    fi

    check_nlp2cmd

    COMMAND="$1"
    shift

    case "$COMMAND" in
        list|--list|-l)
            echo -e "${CYAN}Available Examples (runs in VISIBLE mode by default):${NC}"
            Nlp2cmd examples list
            echo ""
            echo -e "${MAGENTA}💡 Browser window will be shown so you can see the automation!${NC}"
            echo -e "${MAGENTA}   Use --headless to run in background.${NC}"
            ;;
        
        draw)
            if [ $# -eq 0 ]; then
                echo -e "${RED}Error: draw requires a description${NC}"
                echo "Usage: $0 draw \"red star\""
                exit 1
            fi
            DESCRIPTION="$1"
            shift
            echo -e "${CYAN}🎨 Quick draw: $DESCRIPTION${NC}"
            echo -e "${MAGENTA}   Browser VISIBLE mode - watch the magic!${NC}"
            Nlp2cmd examples draw "$DESCRIPTION" "$@"
            ;;
        
        autonomous|auto)
            if [ $# -eq 0 ]; then
                echo -e "${RED}Error: autonomous requires a description${NC}"
                echo "Usage: $0 autonomous \"cat and fish\""
                exit 1
            fi
            DESCRIPTION="$1"
            shift
            echo -e "${CYAN}🧬 Autonomous pipeline: $DESCRIPTION${NC}"
            echo -e "${MAGENTA}   Browser VISIBLE mode - watch the AI work!${NC}"
            Nlp2cmd examples autonomous "$DESCRIPTION" "$@"
            ;;
        
        01_draw_chat|01)
            echo -e "${CYAN}Running: Draw Chat Example${NC}"
            Nlp2cmd examples run 01_draw_chat "$@"
            ;;
        
        02_picsart|02)
            echo -e "${CYAN}Running: Picsart Example${NC}"
            Nlp2cmd examples run 02_picsart "$@"
            ;;
        
        03_adaptive|03)
            echo -e "${CYAN}Running: Adaptive Drawing${NC}"
            Nlp2cmd examples run 03_adaptive "$@"
            ;;
        
        04_object_database|04)
            echo -e "${CYAN}Running: Object Database${NC}"
            Nlp2cmd examples run 04_object_database "$@"
            ;;
        
        05_autonomous|05)
            echo -e "${CYAN}Running: Autonomous Pipeline${NC}"
            Nlp2cmd examples run 05_autonomous "$@"
            ;;
        
        06_visual_validator|06)
            echo -e "${CYAN}Running: Visual Validator${NC}"
            Nlp2cmd examples run 06_visual_validator "$@"
            ;;
        
        07_shape_gallery|07)
            echo -e "${CYAN}Running: Shape Gallery${NC}"
            Nlp2cmd examples run 07_shape_gallery "$@"
            ;;
        
        *)
            # Try to run as nlp2cmd examples command directly
            if Nlp2cmd examples list 2>/dev/null | grep -q "$COMMAND"; then
                Nlp2cmd examples run "$COMMAND" "$@"
            else
                echo -e "${RED}Unknown command: $COMMAND${NC}"
                echo "Run '$0 list' to see available examples"
                exit 1
            fi
            ;;
    esac
}

# Run main
main "$@"
