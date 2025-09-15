#!/usr/bin/env python3
"""
Markdown Renderer for Mermaid and LaTeX
Converts Mermaid diagrams and LaTeX expressions to images in markdown files.

Setup Instructions for macOS:
1. Install Node.js dependencies:
   npm install -g @mermaid-js/mermaid-cli
   
2. Fix Chrome/Puppeteer issues (choose one):
   Option A: Use system Chrome
   export PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
   export PUPPETEER_EXECUTABLE_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
   
   Option B: Install Chrome for Puppeteer
   npx puppeteer browsers install chrome
   
3. Install Python dependencies:
   pip install matplotlib

4. Run the script:
   python3 md_renderer.py input.md
"""

import os
import re
import subprocess
import hashlib
import sys
import json
import shutil
from pathlib import Path

# Try importing matplotlib, provide helpful error if missing
try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    from matplotlib import rcParams
    rcParams['text.usetex'] = False  # Use matplotlib's internal LaTeX renderer
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("Warning: matplotlib not installed. LaTeX rendering disabled.", file=sys.stderr)
    print("Install with: pip install matplotlib", file=sys.stderr)

def check_dependencies():
    """Check if required dependencies are installed."""
    issues = []
    
    # Check for mmdc
    if shutil.which('mmdc') is None:
        issues.append("""
mmdc (Mermaid CLI) not found in PATH.
Install with: npm install -g @mermaid-js/mermaid-cli
""")
    
    # Check if Chrome is accessible for Puppeteer
    chrome_paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        os.path.expanduser("~/.cache/puppeteer/chrome/*/chrome-*/chrome"),
    ]
    
    chrome_found = any(os.path.exists(path) if not '*' in path else bool(list(Path('/').glob(path[1:]))) 
                       for path in chrome_paths)
    
    if not chrome_found and shutil.which('mmdc'):
        # Test if mmdc can actually run
        try:
            result = subprocess.run(['mmdc', '--version'], capture_output=True, timeout=5)
            if result.returncode != 0:
                issues.append("""
Chrome/Chromium not properly configured for Mermaid CLI.
Fix with one of these options:

Option 1 - Use system Chrome:
export PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
export PUPPETEER_EXECUTABLE_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

Option 2 - Install Puppeteer's Chrome:
npx puppeteer browsers install chrome
""")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    
    return issues

def create_output_directory(input_file_path):
    """Creates a directory to store the output files."""
    base_name = os.path.splitext(os.path.basename(input_file_path))[0]
    output_dir = f"{base_name}_processed"
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def setup_mermaid_config(output_dir):
    """Create a Mermaid configuration file for better rendering."""
    config = {
        "theme": "default",
        "themeVariables": {
            "primaryColor": "#fff",
            "primaryTextColor": "#000",
            "primaryBorderColor": "#7C0000",
            "lineColor": "#F8B229",
            "secondaryColor": "#006100",
            "tertiaryColor": "#fff"
        }
    }
    config_path = os.path.join(output_dir, "mermaid.config.json")
    with open(config_path, 'w') as f:
        json.dump(config, f)
    return config_path

def extract_and_replace_mermaid(markdown_content, output_dir):
    """Finds all Mermaid blocks, converts them to images, and replaces them with image links."""
    mermaid_pattern = re.compile(r'```mermaid\s*(.*?)```', re.DOTALL)
    mermaid_blocks = mermaid_pattern.findall(markdown_content)
    
    if not mermaid_blocks:
        return markdown_content
    
    print(f"Found {len(mermaid_blocks)} Mermaid diagram(s)")
    
    # Setup Mermaid config
    config_path = setup_mermaid_config(output_dir)
    
    new_markdown = markdown_content
    for i, block in enumerate(mermaid_blocks):
        temp_mermaid_file = None
        try:
            # Generate a unique filename for the image
            hash_object = hashlib.md5(block.strip().encode())
            filename = f"mermaid_diagram_{i:02d}_{hash_object.hexdigest()[:8]}.png"
            output_path = os.path.join(output_dir, filename)
            
            # Skip if already processed
            if os.path.exists(output_path):
                print(f"  Diagram {i+1}: Already exists, skipping")
                image_link = f"![Mermaid Diagram {i+1}]({filename})"
                new_markdown = mermaid_pattern.sub(image_link, new_markdown, count=1)
                continue
            
            print(f"  Diagram {i+1}: Rendering...", end="")
            
            # Write the mermaid code to a temporary file
            temp_mermaid_file = os.path.join(output_dir, f"temp_mermaid_{i}.mmd")
            with open(temp_mermaid_file, "w") as f:
                f.write(block.strip())
            
            # Prepare mmdc command with proper Chrome path if needed
            cmd = ["mmdc", "-i", temp_mermaid_file, "-o", output_path, 
                   "-c", config_path, "-b", "white", "-w", "800", "-H", "600"]
            
            # Set environment variables for Chrome if on macOS
            env = os.environ.copy()
            if sys.platform == "darwin":
                chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
                if os.path.exists(chrome_path):
                    env["PUPPETEER_EXECUTABLE_PATH"] = chrome_path
                    env["PUPPETEER_SKIP_CHROMIUM_DOWNLOAD"] = "true"
            
            # Run mermaid-cli
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                timeout=30,
                env=env
            )
            
            print(" ✓")
            
            # Replace the mermaid block with an image link
            image_link = f"![Mermaid Diagram {i+1}]({filename})"
            new_markdown = mermaid_pattern.sub(image_link, new_markdown, count=1)
            
        except subprocess.CalledProcessError as e:
            print(f" ✗")
            print(f"    Error: {e.stderr.decode() if e.stderr else str(e)}", file=sys.stderr)
            # Keep original block if conversion fails
        except subprocess.TimeoutExpired:
            print(f" ✗ (timeout)")
            print(f"    Error: Rendering took too long", file=sys.stderr)
        except Exception as e:
            print(f" ✗")
            print(f"    Error: {e}", file=sys.stderr)
        finally:
            # Clean up temporary file
            if temp_mermaid_file and os.path.exists(temp_mermaid_file):
                os.remove(temp_mermaid_file)
    
    # Clean up config file
    if os.path.exists(config_path):
        os.remove(config_path)
    
    return new_markdown

def extract_and_replace_latex(markdown_content, output_dir):
    """Finds all LaTeX expressions, converts them to images, and replaces them with image links."""
    if not HAS_MATPLOTLIB:
        return markdown_content
    
    # Import additional requirements for better rendering
    from matplotlib.patches import Rectangle
    from matplotlib.transforms import Bbox
    
    # Pattern for display math ($...$) and inline math ($...$)
    # More careful pattern to avoid matching dollar signs in text
    display_pattern = re.compile(r'\$\$([^\$]+)\$\$')
    inline_pattern = re.compile(r'(?<!\$)\$(?!\$)([^\$\n]+)\$(?!\$)')
    
    all_matches = []
    for match in display_pattern.finditer(markdown_content):
        all_matches.append(('display', match.group(0), match.group(1)))
    for match in inline_pattern.finditer(markdown_content):
        all_matches.append(('inline', match.group(0), match.group(1)))
    
    if not all_matches:
        return markdown_content
    
    print(f"Found {len(all_matches)} LaTeX expression(s)")
    
    new_markdown = markdown_content
    for i, (math_type, full_expr, latex_content) in enumerate(all_matches):
        try:
            # Generate a unique filename for the image
            hash_object = hashlib.md5(latex_content.encode())
            filename = f"latex_{math_type}_{i:02d}_{hash_object.hexdigest()[:8]}.png"
            output_path = os.path.join(output_dir, filename)
            
            # Skip if already processed
            if os.path.exists(output_path):
                print(f"  Expression {i+1}: Already exists, skipping")
                image_link = f"![LaTeX Expression]({filename})"
                new_markdown = new_markdown.replace(full_expr, image_link, 1)
                continue
            
            print(f"  Expression {i+1} ({math_type}): Rendering...", end="")
            
            # Configure matplotlib for better LaTeX rendering
            dpi = 200  # Higher DPI for sharper images
            
            # Create figure with minimal size
            fig = plt.figure(figsize=(0.1, 0.1), dpi=dpi)
            
            # Create text without axes
            text = fig.text(0, 0, f"${latex_content}$",
                          fontsize=16 if math_type == 'display' else 14,
                          ha='left', va='bottom')
            
            # Get the actual bounding box of the text
            fig.canvas.draw()
            bbox = text.get_window_extent(renderer=fig.canvas.get_renderer())
            
            # Convert bbox to figure coordinates
            bbox_fig = bbox.transformed(fig.transFigure.inverted())
            
            # Calculate tight figure size with 2px padding
            # 2px at given DPI: 2/dpi inches
            padding_inches = 2.0 / dpi
            
            width = bbox_fig.width + (2 * padding_inches)
            height = bbox_fig.height + (2 * padding_inches)
            
            # Create new figure with exact size needed
            plt.close(fig)
            fig = plt.figure(figsize=(width, height), dpi=dpi)
            
            # Position text centered with padding
            fig.text(0.5, 0.5, f"${latex_content}$",
                    fontsize=16 if math_type == 'display' else 14,
                    ha='center', va='center',
                    transform=fig.transFigure)
            
            # Save with fully transparent background and minimal padding
            plt.savefig(output_path,
                       dpi=dpi,
                       transparent=True,
                       bbox_inches='tight',
                       pad_inches=0,  # No additional padding since we added it to figure size
                       format='png',
                       # Ensure no background color
                       facecolor='none',
                       edgecolor='none')
            
            plt.close(fig)
            
            print(" ✓")
            
            # Replace with image link
            image_link = f"![LaTeX Expression]({filename})"
            new_markdown = new_markdown.replace(full_expr, image_link, 1)
            
        except Exception as e:
            print(f" ✗")
            print(f"    Error: {e}", file=sys.stderr)
            # Keep original expression if conversion fails
    
    return new_markdown

def process_markdown_file(input_file_path):
    """Reads a markdown file, processes mermaid and latex, and saves the new markdown and images."""
    # Check dependencies first
    issues = check_dependencies()
    if issues:
        print("⚠️  Dependency issues found:", file=sys.stderr)
        for issue in issues:
            print(issue, file=sys.stderr)
        print("\nContinuing anyway, but some features may not work...\n")
    
    # Read input file
    try:
        with open(input_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: The file '{input_file_path}' was not found.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        return 1
    
    # Create output directory
    output_dir = create_output_directory(input_file_path)
    print(f"Output directory: {output_dir}\n")
    
    # Process Mermaid graphs
    content = extract_and_replace_mermaid(content, output_dir)
    
    # Process LaTeX expressions
    content = extract_and_replace_latex(content, output_dir)
    
    # Write the modified markdown
    output_markdown_path = os.path.join(output_dir, os.path.basename(input_file_path))
    try:
        with open(output_markdown_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"\n✅ Processing complete!")
        print(f"   Output markdown: {output_markdown_path}")
        print(f"   Images saved in: {output_dir}")
    except Exception as e:
        print(f"Error writing output: {e}", file=sys.stderr)
        return 1
    
    return 0

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 md_renderer.py <markdown_file>")
        print("\nThis script converts Mermaid diagrams and LaTeX expressions")
        print("in markdown files to images.")
        sys.exit(1)
    
    input_file = sys.argv[1]
    exit_code = process_markdown_file(input_file)
    sys.exit(exit_code)

if __name__ == "__main__":
    main()