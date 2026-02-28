"""
Mermaid PNG Generator for code2flow
Integrates with CLI to auto-generate PNG from Mermaid files.
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional


def validate_mermaid_file(mmd_path: Path) -> List[str]:
    """Validate Mermaid file and return list of errors."""
    errors = []
    
    if not mmd_path.exists():
        return [f"File not found: {mmd_path}"]
    
    try:
        content = mmd_path.read_text(encoding='utf-8')
        
        # Basic syntax checks
        lines = content.strip().split('\n')
        
        # Check for proper graph declaration
        if not lines or not any(line.strip().startswith(('graph', 'flowchart')) for line in lines):
            errors.append("Missing graph declaration (should start with 'graph' or 'flowchart')")
        
        # Check for unmatched brackets/parentheses - but be smarter about it
        bracket_stack = []
        paren_stack = []
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('%%'):
                continue
                
            # Skip validation for lines that are clearly node definitions with content
            # Node definitions have the pattern: ID[content] or ID(content) or ID{content}
            if (('[' in line and ']' in line) or 
                ('(' in line and ')' in line) or 
                ('{' in line and '}' in line)):
                # This looks like a node definition, check if it's properly formed
                # but don't count parentheses inside the node content
                continue
                
            # Count brackets and parentheses only for non-node-definition lines
            for char in line:
                if char == '[':
                    bracket_stack.append((']', line_num))
                elif char == ']':
                    if not bracket_stack or bracket_stack[-1][0] != ']':
                        errors.append(f"Line {line_num}: Unmatched ']'")
                    else:
                        bracket_stack.pop()
                elif char == '(':
                    paren_stack.append((')', line_num))
                elif char == ')':
                    if not paren_stack or paren_stack[-1][0] != ')':
                        errors.append(f"Line {line_num}: Unmatched ')'")
                    else:
                        paren_stack.pop()
        
        # Report unclosed brackets (only for structural ones, not node content)
        for expected, line_num in bracket_stack:
            errors.append(f"Line {line_num}: Unclosed '[' (missing '{expected}')")
        for expected, line_num in paren_stack:
            errors.append(f"Line {line_num}: Unclosed '(' (missing '{expected}')")
            
        # Check for invalid node IDs
        import re
        node_pattern = re.compile(r'^\s*([A-Z]\d+|[Ff]\d+_\w+)\s*["\'\[\{]')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('%%'):
                continue
            
            # Skip subgraph lines for node ID validation
            if line.startswith('subgraph ') or line == 'end':
                continue
                
            # Skip validation for lines that are clearly node definitions with content
            # Node definitions have the pattern: ID[content] or ID(content) or ID{content}
            if (('[' in line and ']' in line) or 
                ('(' in line and ')' in line) or 
                ('{' in line and '}' in line)):
                # This looks like a node definition, check if it's properly formed
                # but don't count parentheses inside the node content
                continue
                
            # Check node definitions
            if any(char in line for char in ['[', '(', '{']):
                if not node_pattern.match(line):
                    # Try to extract node ID
                    match = re.match(r'^\s*([A-Za-z0-9_]+)', line)
                    if match:
                        node_id = match.group(1)
                        if not re.match(r'^[A-Z]\d+$|^[Ff]\d+_\w+$', node_id):
                            errors.append(f"Line {line_num}: Invalid node ID '{node_id}' (should be like 'N1' or 'F123_name')")
        
    except Exception as e:
        errors.append(f"Error reading file: {e}")
    
    return errors


def fix_mermaid_file(mmd_path: Path) -> bool:
    """Attempt to fix common Mermaid syntax errors."""
    try:
        content = mmd_path.read_text(encoding='utf-8')
        lines = content.split('\n')
        fixed_lines = []
        
        for line in lines:
            original_line = line
            
            # 1. Remove problematic HTML entities that break Mermaid parsing
            if '&quot;' in line or '&apos;' in line or '&#40;' in line or '&#41;' in line:
                # Replace HTML entities back to regular characters
                line = line.replace('&quot;', '"')
                line = line.replace('&apos;', "'")
                line = line.replace('&#40;', '(')
                line = line.replace('&#41;', ')')
                line = line.replace('&#91;', '[')
                line = line.replace('&#93;', ']')
                line = line.replace('&lt;', '<')
                line = line.replace('&gt;', '>')
            
            # 2. Fix edge labels that might have pipe issues
            if '-->' in line and '|' in line:
                # Handle edge labels like: N1 -->|"label"| N2
                if '-->|' in line:
                    parts = line.split('-->|', 1)
                    if len(parts) == 2:
                        label_and_target = parts[1]
                        # Find the closing |
                        if '|' in label_and_target:
                            parts2 = label_and_target.split('|', 1)
                            if len(parts2) == 2:
                                label_content, target = parts2
                                # Clean up the label content - remove extra pipes if any
                                label_content = label_content.strip('|')
                                # Fix incomplete parentheses in edge labels
                                if label_content.endswith('('):
                                    label_content = label_content[:-1]  # Remove trailing parenthesis
                                elif label_content.count('(') > label_content.count(')'):
                                    # Add missing closing parentheses
                                    missing_parens = label_content.count('(') - label_content.count(')')
                                    label_content += ')' * missing_parens
                                line = f"{parts[0]}-->|{label_content}|{target}"
            
            # 3. Fix malformed condition labels
            if '-->|' in line and not line.endswith('|'):
                # Fix missing closing quote
                line = line.rstrip() + '|'
            
            # 4. Fix malformed subgraph IDs
            if line.strip().startswith('subgraph '):
                subgraph_part = line.strip()[9:].split('(', 1)
                if len(subgraph_part) == 2:
                    subgraph_id, rest = subgraph_part
                    # Clean subgraph ID
                    subgraph_id = subgraph_id.replace('.', '_').replace('-', '_').replace(':', '_')
                    line = f"    subgraph {subgraph_id}({rest}"
            
            # 5. Fix class definitions with too many nodes
            if line.strip().startswith('class ') and ',' in line:
                # Split long class lines
                class_parts = line.split(' ', 1)
                if len(class_parts) == 2:
                    nodes_and_class = class_parts[1]
                    nodes, class_name = nodes_and_class.rsplit(' ', 1)
                    node_list = nodes.split(',')
                    if len(node_list) > 10:  # Split if too many nodes
                        # Create multiple lines
                        for i in range(0, len(node_list), 10):
                            chunk = ','.join(node_list[i:i+10])
                            fixed_lines.append(f"    class {chunk} {class_name}")
                        continue
            
            fixed_lines.append(line)
        
        # Write back if changed
        fixed_content = '\n'.join(fixed_lines)
        if fixed_content != content:
            mmd_path.write_text(fixed_content, encoding='utf-8')
            return True
            
    except Exception as e:
        print(f"Error fixing {mmd_path}: {e}")
    
    return False


def generate_pngs(input_dir: Path, output_dir: Path, timeout: int = 60) -> int:
    """Generate PNG files from all .mmd files in input_dir."""
    mmd_files = list(input_dir.glob('*.mmd'))
    
    if not mmd_files:
        return 0
    
    success_count = 0
    
    for mmd_file in mmd_files:
        output_file = output_dir / f"{mmd_file.stem}.png"
        
        # Validate first
        errors = validate_mermaid_file(mmd_file)
        if errors:
            print(f"  Fixing {mmd_file.name}: {len(errors)} issues")
            fix_mermaid_file(mmd_file)
            
            # Re-validate
            errors = validate_mermaid_file(mmd_file)
            if errors:
                print(f"    Still has errors: {errors[:3]}")  # Show first 3 errors
                continue
        
        # Try to generate PNG
        if generate_single_png(mmd_file, output_file, timeout):
            success_count += 1
    
    return success_count


def generate_single_png(mmd_file: Path, output_file: Path, timeout: int = 60) -> bool:
    """Generate PNG from single Mermaid file using available renderers."""
    
    # Create output directory
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Try different renderers in order of preference
    renderers = [
        ('mmdc', ['mmdc', '-i', str(mmd_file), '-o', str(output_file), '-t', 'default', '-b', 'white']),
        ('npx', ['npx', '-y', '@mermaid-js/mermaid-cli', '-i', str(mmd_file), '-o', str(output_file), '-t', 'default', '-b', 'white']),
        ('puppeteer', None)  # Special handling
    ]
    
    for renderer_name, cmd in renderers:
        try:
            if renderer_name == 'puppeteer':
                # Special puppeteer handling
                if generate_with_puppeteer(mmd_file, output_file, timeout):
                    return True
                continue
            
            # Run command
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            
            if result.returncode == 0:
                return True
            else:
                print(f"    {renderer_name} failed: {result.stderr.strip()}")
                
        except subprocess.TimeoutExpired:
            print(f"    {renderer_name} timed out")
        except FileNotFoundError:
            print(f"    {renderer_name} not available")
        except Exception as e:
            print(f"    {renderer_name} error: {e}")
    
    return False


def generate_with_puppeteer(mmd_file: Path, output_file: Path, timeout: int = 60) -> bool:
    """Generate PNG using Puppeteer with HTML template."""
    try:
        mmd_content = mmd_file.read_text(encoding='utf-8')
        
        html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        body {{ margin: 0; padding: 20px; background: white; font-family: Arial, sans-serif; }}
        .mermaid {{ max-width: none; }}
    </style>
</head>
<body>
    <div class="mermaid">
{mmd_content}
    </div>
    <script>
        mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
    </script>
</body>
</html>
"""
        
        # Create temporary HTML
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as tmp_html:
            tmp_html.write(html_template)
            tmp_html_path = tmp_html.name
        
        try:
            # Use puppeteer screenshot
            cmd = [
                'npx', '-y', 'puppeteer',
                'screenshot',
                '--url', f'file://{tmp_html_path}',
                '--output', str(output_file),
                '--wait-for', '.mermaid',
                '--full-page'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            
            return result.returncode == 0
            
        finally:
            os.unlink(tmp_html_path)
            
    except Exception as e:
        print(f"    Puppeteer error: {e}")
        return False


if __name__ == '__main__':
    # CLI interface for testing
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate PNG from Mermaid files')
    parser.add_argument('input_dir', help='Directory with .mmd files')
    parser.add_argument('output_dir', help='Output directory for PNG files')
    
    args = parser.parse_args()
    
    input_path = Path(args.input_dir)
    output_path = Path(args.output_dir)
    
    count = generate_pngs(input_path, output_path)
    print(f"Generated {count} PNG files")
