#!/bin/bash

# https://claude.ai/chat/719c949f-a8a8-43cc-a5f2-fb6f71cf133a

# Setup script for Markdown Renderer on macOS
# This script installs all necessary dependencies

set -e  # Exit on error

echo "🚀 Markdown Renderer Setup for macOS"
echo "===================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check for Homebrew
echo "Checking for Homebrew..."
if ! command_exists brew; then
    print_warning "Homebrew not found. Installing..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to PATH for Apple Silicon Macs
    if [[ -f "/opt/homebrew/bin/brew" ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
else
    print_status "Homebrew is installed"
fi

# Check for Node.js
echo ""
echo "Checking for Node.js..."
if ! command_exists node; then
    print_warning "Node.js not found. Installing via Homebrew..."
    brew install node
else
    NODE_VERSION=$(node --version)
    print_status "Node.js is installed (${NODE_VERSION})"
fi

# Check for npm
echo ""
echo "Checking for npm..."
if ! command_exists npm; then
    print_error "npm not found. This should have been installed with Node.js"
    exit 1
else
    NPM_VERSION=$(npm --version)
    print_status "npm is installed (${NPM_VERSION})"
fi

# Install Mermaid CLI globally
echo ""
echo "Installing Mermaid CLI..."
if ! command_exists mmdc; then
    npm install -g @mermaid-js/mermaid-cli
    print_status "Mermaid CLI installed"
else
    print_status "Mermaid CLI already installed"
fi

# Check for Chrome
echo ""
echo "Checking for Chrome/Chromium..."
CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CHROMIUM_PATH="/Applications/Chromium.app/Contents/MacOS/Chromium"

if [[ -f "$CHROME_PATH" ]]; then
    print_status "Google Chrome found"
    export PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
    export PUPPETEER_EXECUTABLE_PATH="$CHROME_PATH"
    
    # Add to shell profile
    SHELL_PROFILE="$HOME/.zshrc"
    if [[ "$SHELL" == *"bash"* ]]; then
        SHELL_PROFILE="$HOME/.bash_profile"
    fi
    
    if ! grep -q "PUPPETEER_EXECUTABLE_PATH" "$SHELL_PROFILE" 2>/dev/null; then
        echo "" >> "$SHELL_PROFILE"
        echo "# Puppeteer Chrome configuration" >> "$SHELL_PROFILE"
        echo "export PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true" >> "$SHELL_PROFILE"
        echo "export PUPPETEER_EXECUTABLE_PATH=\"$CHROME_PATH\"" >> "$SHELL_PROFILE"
        print_status "Added Chrome path to $SHELL_PROFILE"
    fi
elif [[ -f "$CHROMIUM_PATH" ]]; then
    print_status "Chromium found"
    export PUPPETEER_EXECUTABLE_PATH="$CHROMIUM_PATH"
else
    print_warning "Chrome/Chromium not found in standard locations"
    echo "Installing Puppeteer's bundled Chrome..."
    npx puppeteer browsers install chrome
fi

# Test mmdc
echo ""
echo "Testing Mermaid CLI..."
if mmdc --version >/dev/null 2>&1; then
    MMDC_VERSION=$(mmdc --version 2>/dev/null | head -n1)
    print_status "Mermaid CLI is working (${MMDC_VERSION})"
else
    print_error "Mermaid CLI test failed"
    echo "Trying to fix Chrome/Puppeteer integration..."
    npx puppeteer browsers install chrome
fi

# Python dependencies (for Python version)
echo ""
echo "Checking Python dependencies..."
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version)
    print_status "Python3 found (${PYTHON_VERSION})"
    
    # Check for pip
    if command_exists pip3; then
        echo "Installing Python dependencies..."
        pip3 install matplotlib
        print_status "matplotlib installed"
    else
        print_warning "pip3 not found. Install with: python3 -m ensurepip"
    fi
else
    print_warning "Python3 not found. Python version will not work"
fi

# Node.js project setup (for Node.js version)
echo ""
echo "Setting up Node.js project..."
if [[ ! -f "package.json" ]]; then
    npm init -y >/dev/null 2>&1
    print_status "Created package.json"
fi

echo "Installing Node.js dependencies..."
npm install @mermaid-js/mermaid-cli puppeteer crypto
npm install --save-optional mathjax-node

print_status "Node.js dependencies installed"

# Create test markdown file
echo ""
echo "Creating test file..."
cat > test.md << 'EOF'
# Test Markdown File

This is a test file with Mermaid diagrams and LaTeX expressions.

## Mermaid Diagram

```mermaid
graph TD
    A[Start] --> B{Is it working?}
    B -->|Yes| C[Great!]
    B -->|No| D[Debug]
    D --> A
```

## LaTeX Math

Here's an inline equation: $E = mc^2$

And a display equation:

$$\int_{a}^{b} f(x) dx = F(b) - F(a)$$

## Another Mermaid Diagram

```mermaid
sequenceDiagram
    participant User
    participant Script
    participant Mermaid
    User->>Script: Run script
    Script->>Mermaid: Convert diagram
    Mermaid->>Script: Return image
    Script->>User: Show result
```

The quadratic formula: $x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$
EOF

print_status "Created test.md"

# Final instructions
echo ""
echo "===================================="
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo ""
echo "You can now use the markdown renderer:"
echo ""
echo "  Python version:"
echo "    python3 md_renderer.py test.md"
echo ""
echo "  Node.js version:"
echo "    node md_renderer.js test.md"
echo ""
echo "Both scripts will:"
echo "  1. Create a 'test_processed' folder"
echo "  2. Generate images for all diagrams and equations"
echo "  3. Create a new markdown file with image references"
echo ""

# Test run option
read -p "Would you like to run a test now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [[ -f "md_renderer.js" ]]; then
        echo "Running Node.js version..."
        node md_renderer.js test.md
    elif [[ -f "md_renderer.py" ]]; then
        echo "Running Python version..."
        python3 md_renderer.py test.md
    else
        print_error "No renderer script found. Please save md_renderer.js or md_renderer.py first."
    fi
fi