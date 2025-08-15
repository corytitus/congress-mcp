#!/bin/bash

echo "🔐 EnactAI MCP Server - Claude Authentication Setup"
echo "==================================================="
echo ""

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

# Detect OS and Claude config location
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    CLAUDE_CONFIG_DIR="$HOME/Library/Application Support/Claude"
    CLAUDE_CONFIG_FILE="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Windows
    CLAUDE_CONFIG_DIR="$APPDATA/Claude"
    CLAUDE_CONFIG_FILE="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"
else
    # Linux
    CLAUDE_CONFIG_DIR="$HOME/.config/Claude"
    CLAUDE_CONFIG_FILE="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"
fi

echo "📁 Claude config location: $CLAUDE_CONFIG_FILE"
echo ""

# Create config directory if it doesn't exist
mkdir -p "$CLAUDE_CONFIG_DIR"

# Step 1: Create a token
echo "Step 1: Creating API token for Claude..."
echo "-----------------------------------------"

cd "$SCRIPT_DIR"
output=$(python3 token_manager.py create "Claude Desktop" --permissions standard 2>&1)
token=$(echo "$output" | grep "Token: " | cut -d' ' -f2)
token_id=$(echo "$output" | grep "ID: " | cut -d' ' -f2)

if [ -z "$token" ]; then
    echo "❌ Failed to create token"
    exit 1
fi

echo "✅ Token created successfully!"
echo ""

# Step 2: Update Claude Desktop config
echo "Step 2: Updating Claude Desktop configuration..."
echo "------------------------------------------------"

# Create the MCP server config
MCP_CONFIG=$(cat <<EOF
{
  "mcpServers": {
    "enactai-data-auth": {
      "command": "$SCRIPT_DIR/run_auth.sh"
    }
  }
}
EOF
)

# Check if config file exists
if [ -f "$CLAUDE_CONFIG_FILE" ]; then
    echo "⚠️  Claude config already exists. Backing up to $CLAUDE_CONFIG_FILE.backup"
    cp "$CLAUDE_CONFIG_FILE" "$CLAUDE_CONFIG_FILE.backup"
    
    # Merge with existing config (this is simplified - for production use jq)
    echo "📝 Please manually add this to your $CLAUDE_CONFIG_FILE:"
    echo ""
    echo '  "enactai-data-auth": {'
    echo '    "command": "'$SCRIPT_DIR'/run_auth.sh"'
    echo '  }'
    echo ""
else
    # Create new config
    echo "$MCP_CONFIG" > "$CLAUDE_CONFIG_FILE"
    echo "✅ Claude Desktop configuration created!"
fi

# Step 3: Save token info
TOKEN_FILE="$SCRIPT_DIR/.claude_token"
cat > "$TOKEN_FILE" <<EOF
# Claude Desktop Authentication Token
# Created: $(date)
TOKEN_ID=$token_id
TOKEN=$token
EOF
chmod 600 "$TOKEN_FILE"

echo ""
echo "=============================================="
echo "🎉 Setup Complete!"
echo "=============================================="
echo ""
echo "📋 Your authentication token:"
echo ""
echo "  $token"
echo ""
echo "Token saved to: $TOKEN_FILE"
echo ""
echo "🚀 Next Steps:"
echo "1. Restart Claude Desktop"
echo "2. In a new conversation, authenticate with:"
echo "   'Use the authenticate tool with token: $token'"
echo ""
echo "📊 Token Management Commands:"
echo "  python3 token_manager.py list        # List all tokens"
echo "  python3 token_manager.py stats $token_id  # View usage"
echo "  python3 token_manager.py revoke $token_id # Revoke token"
echo ""
echo "=============================================="