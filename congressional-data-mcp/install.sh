#!/bin/bash
# Congressional Data MCP - One-Click Installer
# No coding experience required!

set -e  # Exit on any error

# Colors for pretty output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print with colors
print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[✓]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
print_error() { echo -e "${RED}[✗]${NC} $1"; }

clear
echo "=========================================="
echo "   Congressional Data MCP Installer"
echo "   No coding experience required!"
echo "=========================================="
echo ""

# Step 1: Check operating system
print_status "Checking your operating system..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="mac"
    print_success "macOS detected"
    CLAUDE_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    print_success "Linux detected"
    CLAUDE_CONFIG="$HOME/.config/Claude/claude_desktop_config.json"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
    print_success "Windows detected"
    CLAUDE_CONFIG="$APPDATA/Claude/claude_desktop_config.json"
else
    print_error "Unsupported operating system: $OSTYPE"
    exit 1
fi

# Step 2: Check for Python
print_status "Checking for Python..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
    print_success "Python $PYTHON_VERSION found"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
    PYTHON_VERSION=$(python --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
    print_success "Python $PYTHON_VERSION found"
else
    print_error "Python is not installed!"
    print_warning "Please install Python 3.9 or later from: https://www.python.org/downloads/"
    exit 1
fi

# Step 3: Install Python packages
print_status "Installing required Python packages..."
print_warning "This may take a few minutes..."

# Create a virtual environment to avoid conflicts
if [ ! -d "venv" ]; then
    $PYTHON_CMD -m venv venv 2>/dev/null || {
        print_warning "Creating virtual environment failed, installing globally..."
        VENV_FAILED=true
    }
fi

# Activate virtual environment or use global
if [ "$VENV_FAILED" != "true" ]; then
    if [ "$OS" == "windows" ]; then
        source venv/Scripts/activate 2>/dev/null || true
    else
        source venv/bin/activate 2>/dev/null || true
    fi
    PIP_CMD="pip"
else
    PIP_CMD="$PYTHON_CMD -m pip"
fi

# Install packages
$PIP_CMD install --quiet --upgrade pip 2>/dev/null || true
$PIP_CMD install --quiet \
    mcp httpx structlog aiolimiter python-dotenv 2>/dev/null || {
    print_warning "Some packages might not have installed correctly"
}

print_success "Python packages installed"

# Step 4: Get API keys
echo ""
echo "=========================================="
echo "   API Key Setup (Required)"
echo "=========================================="
echo ""
echo "You need two FREE API keys to use this tool:"
echo ""
echo "1. Congress.gov API Key"
echo "   Sign up here: https://api.congress.gov/sign-up/"
echo ""
echo "2. GovInfo API Key"
echo "   Sign up here: https://api.data.gov/signup/"
echo ""
print_warning "These are FREE government APIs - no credit card required!"
echo ""

# Check if .env already has keys
if [ -f ".env" ]; then
    source .env
    if [ ! -z "$CONGRESS_GOV_API_KEY" ] && [ "$CONGRESS_GOV_API_KEY" != "your-congress-api-key-here" ]; then
        print_success "Found existing Congress.gov API key"
        CONGRESS_KEY="$CONGRESS_GOV_API_KEY"
    fi
    if [ ! -z "$GOVINFO_API_KEY" ] && [ "$GOVINFO_API_KEY" != "your-govinfo-api-key-here" ]; then
        print_success "Found existing GovInfo API key"
        GOVINFO_KEY="$GOVINFO_API_KEY"
    fi
fi

# Ask for Congress.gov key if not found
if [ -z "$CONGRESS_KEY" ]; then
    echo -n "Enter your Congress.gov API key: "
    read CONGRESS_KEY
    if [ -z "$CONGRESS_KEY" ]; then
        print_error "Congress.gov API key is required!"
        exit 1
    fi
fi

# Ask for GovInfo key if not found
if [ -z "$GOVINFO_KEY" ]; then
    echo -n "Enter your GovInfo API key: "
    read GOVINFO_KEY
    if [ -z "$GOVINFO_KEY" ]; then
        print_error "GovInfo API key is required!"
        exit 1
    fi
fi

# Step 5: Create .env file
print_status "Saving your API keys..."
cat > .env << EOF
# Congressional Data MCP API Keys
CONGRESS_GOV_API_KEY=$CONGRESS_KEY
GOVINFO_API_KEY=$GOVINFO_KEY

# Configuration
MCP_SERVER_NAME=congressional-data-mcp
ENABLE_CACHING=false
DOCKER_MODE=false
EOF
print_success "API keys saved to .env file"

# Step 6: Configure Claude Desktop
print_status "Configuring Claude Desktop..."

# Get current directory
CURRENT_DIR=$(pwd)

# Check if Claude config exists
if [ ! -f "$CLAUDE_CONFIG" ]; then
    print_warning "Claude Desktop configuration not found"
    print_status "Creating new configuration..."
    mkdir -p "$(dirname "$CLAUDE_CONFIG")"
    echo '{"mcpServers":{}}' > "$CLAUDE_CONFIG"
fi

# Create Python wrapper script with embedded environment
print_status "Creating launcher script..."
cat > run_mcp.sh << EOF
#!/bin/bash
cd "$CURRENT_DIR"
export CONGRESS_GOV_API_KEY="$CONGRESS_KEY"
export GOVINFO_API_KEY="$GOVINFO_KEY"
export PYTHONPATH="$CURRENT_DIR"
export DOCKER_MODE=false
export ENABLE_CACHING=false
EOF

if [ "$VENV_FAILED" != "true" ]; then
    echo "source $CURRENT_DIR/venv/bin/activate 2>/dev/null || true" >> run_mcp.sh
    echo "python $CURRENT_DIR/server.py" >> run_mcp.sh
else
    echo "$PYTHON_CMD $CURRENT_DIR/server.py" >> run_mcp.sh
fi

chmod +x run_mcp.sh

# Add to Claude config using Python for JSON manipulation
$PYTHON_CMD << EOF
import json
import os

config_path = "$CLAUDE_CONFIG"
current_dir = "$CURRENT_DIR"

# Read existing config
try:
    with open(config_path, 'r') as f:
        config = json.load(f)
except:
    config = {"mcpServers": {}}

# Add our server
config["mcpServers"]["congressional-data"] = {
    "command": "bash",
    "args": [os.path.join(current_dir, "run_mcp.sh")]
}

# Write updated config
with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print("✓ Claude Desktop configuration updated")
EOF

# Step 7: Test the installation
print_status "Testing the installation..."
$PYTHON_CMD << EOF
import sys
import os
os.environ['CONGRESS_GOV_API_KEY'] = "$CONGRESS_KEY"
os.environ['GOVINFO_API_KEY'] = "$GOVINFO_KEY"
os.environ['DOCKER_MODE'] = "false"
os.environ['ENABLE_CACHING'] = "false"

try:
    import mcp
    import httpx
    import structlog
    import aiolimiter
    print("✓ All packages working correctly")
except ImportError as e:
    print(f"✗ Missing package: {e}")
    sys.exit(1)

# Test API keys
if "$CONGRESS_KEY" and "$CONGRESS_KEY" != "your-congress-api-key-here":
    print("✓ Congress.gov API key configured")
else:
    print("✗ Congress.gov API key missing")
    
if "$GOVINFO_KEY" and "$GOVINFO_KEY" != "your-govinfo-api-key-here":
    print("✓ GovInfo API key configured")
else:
    print("✗ GovInfo API key missing")
EOF

echo ""
echo "=========================================="
echo "   Installation Complete! 🎉"
echo "=========================================="
echo ""
print_success "Congressional Data MCP is ready to use!"
echo ""
echo "Next steps:"
echo "1. ${GREEN}Restart Claude Desktop${NC}"
echo "2. You'll see 'congressional-data' in your MCP servers"
echo "3. Try asking Claude:"
echo "   - 'Search for recent bills about healthcare'"
echo "   - 'Find information about Senator Smith'"
echo "   - 'What bills were voted on this week?'"
echo ""
print_warning "Important: You must restart Claude Desktop for changes to take effect"
echo ""
echo "For help, visit: https://github.com/yourusername/congressional-data-mcp"
echo ""