#!/bin/bash

echo "🔐 EnactAI MCP Server - Authentication Setup"
echo "============================================"
echo ""

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

# Create initial admin token
echo "Creating your first API token..."
echo ""

read -p "Enter a name for this token (e.g., 'My Development Token'): " token_name
if [ -z "$token_name" ]; then
    token_name="Default Admin Token"
fi

echo ""
echo "Select permission level:"
echo "1) read_only  - Can only read data"
echo "2) standard   - Can read and perform standard operations"
echo "3) admin      - Full access to all operations"
echo ""
read -p "Choose (1-3, default is 2): " perm_choice

case $perm_choice in
    1)
        permissions="read_only"
        ;;
    3)
        permissions="admin"
        ;;
    *)
        permissions="standard"
        ;;
esac

# Create the token
echo ""
echo "Creating token..."
output=$(python3 token_manager.py create "$token_name" --permissions "$permissions" 2>&1)
echo "$output"

# Extract the token from output
token=$(echo "$output" | grep "Token: " | cut -d' ' -f2)

if [ -n "$token" ]; then
    echo ""
    echo "=========================================="
    echo "🎉 Token created successfully!"
    echo "=========================================="
    echo ""
    echo "Save this token securely - it cannot be retrieved again:"
    echo ""
    echo "  $token"
    echo ""
    echo "To use this token:"
    echo ""
    echo "1. Start the authenticated server:"
    echo "   REQUIRE_AUTH=true python3 enactai_server_local_auth.py"
    echo ""
    echo "2. In your MCP client, first authenticate:"
    echo "   Use the 'authenticate' tool with your token"
    echo ""
    echo "3. Then use any permitted tools based on your permissions"
    echo ""
    echo "=========================================="
    echo ""
    echo "Other useful commands:"
    echo "  python3 token_manager.py list      # List all tokens"
    echo "  python3 token_manager.py stats ID  # View token usage"
    echo "  python3 token_manager.py revoke ID # Revoke a token"
    echo ""
else
    echo "❌ Failed to create token. Please check the error above."
    exit 1
fi