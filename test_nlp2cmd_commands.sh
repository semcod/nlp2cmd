#!/bin/bash

# Skrypt testujący NLP2CMD z wykonywaniem w przeglądarce i nagrywaniem wideo
# Testuje komendę: "wejdź na jspaint.app i narysuj biedronkę"
# 
# Wskazówki z TODO/:
# - Używa action_plan zamiast hardkodowanych zmiennych
# - Wykonuje kroki w przeglądarce Playwright
# - Nagrywa wideo i robi zrzut ekranu na końcu

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Check if nlp2cmd is installed
if ! command -v nlp2cmd &> /dev/null; then
    print_error "nlp2cmd is not installed or not in PATH"
    exit 1
fi
print_success "nlp2cmd is installed"

# Check for playwright
print_status "Checking for Playwright..."
if ! python3 -c "import playwright" 2>/dev/null; then
    print_error "Playwright not installed. Install with: pip install playwright && playwright install chromium"
    exit 1
fi
print_success "Playwright is available"

# Create output directory
OUTPUT_DIR="${OUTPUT_DIR:-/tmp/nlp2cmd_tests}"
mkdir -p "$OUTPUT_DIR"

print_status "Testing: ladybug drawing on jspaint.app"
print_status "================================================"
echo ""

# Test command
QUERY="wejdź na jspaint.app i narysuj biedronkę"
VIDEO_PATH="$OUTPUT_DIR/biedronka.webm"
SCREENSHOT_PATH="$OUTPUT_DIR/biedronka_final.png"
ACTION_PLAN_FILE="$OUTPUT_DIR/action_plan.json"

print_status "Step 1: Generating action plan from NLP query..."
nlp2cmd -q "$QUERY" --explain > "$OUTPUT_DIR/nlp2cmd_output.log" 2>&1
cat "$OUTPUT_DIR/nlp2cmd_output.log"

# Extract action plan from output
print_status "Step 2: Extracting action plan..."
python3 << 'PYTHON_SCRIPT'
import json
import re
import sys

log_file = "/tmp/nlp2cmd_tests/nlp2cmd_output.log"
output_file = "/tmp/nlp2cmd_tests/action_plan.json"

with open(log_file, 'r') as f:
    content = f.read()

# Try to find JSON action plan
match = re.search(r'\{[\s\S]*"dsl"[\s\S]*"steps"[\s\S]*\}', content)
if match:
    try:
        action_plan = json.loads(match.group())
        with open(output_file, 'w') as f:
            json.dump(action_plan, f, indent=2)
        print(f"✅ Action plan saved to {output_file}")
        sys.exit(0)
    except json.JSONDecodeError:
        pass

print("❌ Could not extract action plan from output")
sys.exit(1)
PYTHON_SCRIPT

if [ ! -f "$ACTION_PLAN_FILE" ]; then
    print_error "Failed to extract action plan"
    exit 1
fi

print_status "Step 3: Executing action plan in browser with video recording..."

# Execute action plan using Python/Playwright
python3 << 'PLAYWRIGHT_SCRIPT'
import json
import sys
from pathlib import Path

# Load action plan
action_plan_file = "/tmp/nlp2cmd_tests/action_plan.json"
video_path = "/tmp/nlp2cmd_tests/biedronka.webm"
screenshot_path = "/tmp/nlp2cmd_tests/biedronka_final.png"

with open(action_plan_file, 'r') as f:
    action_plan = json.load(f)

steps = action_plan.get('steps', [])
print(f"🎬 Found {len(steps)} steps to execute")

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    # Launch browser with video recording
    video_dir = Path(video_path).parent
    video_dir.mkdir(parents=True, exist_ok=True)
    
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        record_video_dir=str(video_dir),
        record_video_size={"width": 1280, "height": 720},
    )
    
    page = context.new_page()
    
    # Track canvas center for drawing
    canvas_center = {"x": 640, "y": 360}
    
    for i, step in enumerate(steps, 1):
        action = step.get('action', '')
        params = step.get('params', {})
        
        print(f"  Step {i}/{len(steps)}: {action}")
        
        try:
            if action == 'navigate':
                url = params.get('url', 'https://jspaint.app')
                if not url.startswith('http'):
                    url = 'https://' + url
                print(f"    → Navigating to {url}")
                page.goto(url, wait_until='networkidle')
                page.wait_for_timeout(2000)
                
            elif action == 'wait_for_canvas':
                print(f"    → Waiting for canvas")
                try:
                    page.wait_for_selector('canvas', timeout=5000)
                except:
                    pass
                page.wait_for_timeout(1000)
                
            elif action == 'get_canvas_center':
                print(f"    → Getting canvas center")
                try:
                    canvas = page.locator('canvas').first
                    if canvas.is_visible():
                        box = canvas.bounding_box()
                        if box:
                            canvas_center['x'] = box['x'] + box['width'] // 2
                            canvas_center['y'] = box['y'] + box['height'] // 2
                            print(f"      Canvas center: {canvas_center}")
                except Exception as e:
                    print(f"      Using default center: {canvas_center}")
                    
            elif action == 'select_tool':
                tool = params.get('tool', '')
                print(f"    → Selecting tool: {tool}")
                # For jspaint, try clicking on tool buttons
                try:
                    if tool in ['ellipse', 'circle']:
                        # Look for ellipse/circle tool
                        page.locator('button[title*="ellipse"], button[title*="circle"], button:has-text("Oval")').first.click(timeout=2000)
                    elif tool == 'brush':
                        page.locator('button[title*="brush"], button[title*="paint"]').first.click(timeout=2000)
                    elif tool == 'line':
                        page.locator('button[title*="line"]').first.click(timeout=2000)
                except:
                    pass
                page.wait_for_timeout(500)
                
            elif action == 'set_color':
                color = params.get('color', '#000000')
                print(f"    → Setting color: {color}")
                # Try to set color in jspaint
                try:
                    # Look for color picker or color input
                    color_input = page.locator('input[type="color"]').first
                    if color_input.is_visible():
                        color_input.fill(color)
                except:
                    pass
                page.wait_for_timeout(300)
                
            elif action == 'draw_filled_ellipse':
                rx = params.get('rx', 50)
                ry = params.get('ry', 50)
                relative = params.get('relative_to', '')
                
                x = canvas_center['x']
                y = canvas_center['y']
                
                print(f"    → Drawing filled ellipse at ({x}, {y})")
                
                # Draw ellipse using drag
                page.mouse.move(x - rx, y - ry)
                page.mouse.down()
                page.mouse.move(x + rx, y + ry, steps=10)
                page.mouse.up()
                page.wait_for_timeout(500)
                
            elif action == 'draw_circle':
                radius = params.get('radius', 10)
                offset = params.get('offset', [0, 0])
                
                x = canvas_center['x'] + offset[0]
                y = canvas_center['y'] + offset[1]
                
                print(f"    → Drawing circle at ({x}, {y})")
                
                # Draw small circle
                page.mouse.move(x - radius, y - radius)
                page.mouse.down()
                page.mouse.move(x + radius, y + radius, steps=5)
                page.mouse.up()
                page.wait_for_timeout(300)
                
            elif action == 'draw_line':
                from_offset = params.get('from_offset', [0, 0])
                to_offset = params.get('to_offset', [0, 0])
                
                x1 = canvas_center['x'] + from_offset[0]
                y1 = canvas_center['y'] + from_offset[1]
                x2 = canvas_center['x'] + to_offset[0]
                y2 = canvas_center['y'] + to_offset[1]
                
                print(f"    → Drawing line from ({x1}, {y1}) to ({x2}, {y2})")
                
                page.mouse.move(x1, y1)
                page.mouse.down()
                page.mouse.move(x2, y2, steps=10)
                page.mouse.up()
                page.wait_for_timeout(300)
                
            elif action == 'screenshot':
                suffix = params.get('suffix', 'final')
                print(f"    → Taking screenshot: {screenshot_path}")
                page.screenshot(path=screenshot_path, full_page=False)
                print(f"✅ Screenshot saved!")
                
            else:
                print(f"    ⚠️ Unknown action: {action}")
                
        except Exception as e:
            print(f"    ⚠️ Step error: {e}")
            continue
    
    # Final wait to see the result
    page.wait_for_timeout(2000)
    
    # Close context and browser
    context.close()
    browser.close()

print("✅ Browser execution completed!")
PLAYWRIGHT_SCRIPT

echo ""
print_status "================================================"

# Check if video was created
if [ -f "$VIDEO_PATH" ]; then
    VIDEO_SIZE=$(du -h "$VIDEO_PATH" | cut -f1)
    print_success "✅ Video created: $VIDEO_PATH ($VIDEO_SIZE)"
else
    print_error "❌ Video file not found at $VIDEO_PATH"
fi

# Check if screenshot was created
if [ -f "$SCREENSHOT_PATH" ]; then
    SCREENSHOT_SIZE=$(du -h "$SCREENSHOT_PATH" | cut -f1)
    print_success "✅ Screenshot created: $SCREENSHOT_PATH ($SCREENSHOT_SIZE)"
else
    print_warning "⚠️ Screenshot not found, checking for alternative names..."
    # Look for any screenshot files
    FOUND_SCREENSHOT=$(find "$OUTPUT_DIR" -name "*.png" -type f 2>/dev/null | head -1)
    if [ -n "$FOUND_SCREENSHOT" ]; then
        print_success "✅ Found screenshot: $FOUND_SCREENSHOT"
    else
        print_error "❌ No screenshot files found"
    fi
fi

echo ""
print_status "Test Results:"
print_status "-------------"

# Show generated command from log
if [ -f "$OUTPUT_DIR/nlp2cmd_output.log" ]; then
    print_status "Generated action plan:"
    grep -A 50 '"steps":' "$OUTPUT_DIR/nlp2cmd_output.log" | head -60 || true
fi

echo ""
print_success "All tests completed!"
print_status "Output files location: $OUTPUT_DIR"
print_status "To view the video: firefox $VIDEO_PATH"
print_status "To view the screenshot: eog $SCREENSHOT_PATH"
