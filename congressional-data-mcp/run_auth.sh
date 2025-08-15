#!/bin/bash

# EnactAI MCP Server Launcher with Authentication
# This script starts the authenticated MCP server for Claude Desktop

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Use the correct Python path
PYTHON_CMD="/opt/homebrew/bin/python3"

# Load environment variables if .env exists
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set authentication requirement (default: enabled)
export REQUIRE_AUTH=${REQUIRE_AUTH:-true}

# Set API keys if not already set
export CONGRESS_GOV_API_KEY=${CONGRESS_GOV_API_KEY:-""}
export GOVINFO_API_KEY=${GOVINFO_API_KEY:-""}

# Set token secret key (generates one if not set)
if [ -z "$TOKEN_SECRET_KEY" ]; then
    export TOKEN_SECRET_KEY=$($PYTHON_CMD -c "import secrets; print(secrets.token_hex(32))")
    echo "TOKEN_SECRET_KEY=$TOKEN_SECRET_KEY" >> .env 2>/dev/null
fi

echo "🔐 Starting EnactAI MCP Server with Authentication" >&2
echo "==================================================" >&2
echo "" >&2

# Check if tokens exist
token_count=$($PYTHON_CMD -c "from token_manager import TokenManager; m = TokenManager(); print(len(m.list_tokens()))" 2>/dev/null || echo "0")

if [ "$token_count" = "0" ]; then
    echo "⚠️  No API tokens found!" >&2
    echo "" >&2
    echo "Creating your first token..." >&2
    echo "" >&2
    
    # Create a default token
    output=$($PYTHON_CMD token_manager.py create "Claude Desktop Token" --permissions standard 2>&1)
    token=$(echo "$output" | grep "Token: " | cut -d' ' -f2)
    
    if [ -n "$token" ]; then
        echo "✅ Created token for Claude Desktop" >&2
        echo "" >&2
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
        echo "IMPORTANT: Save this token (it won't be shown again):" >&2
        echo "" >&2
        echo "  $token" >&2
        echo "" >&2
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
        echo "" >&2
        echo "In Claude Desktop, use the 'authenticate' tool with this token" >&2
        echo "" >&2
    fi
else
    echo "✅ Found $token_count existing token(s)" >&2
    echo "" >&2
    echo "Tokens:" >&2
    $PYTHON_CMD token_manager.py list >&2
    echo "" >&2
fi

echo "Starting server..." >&2
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2

# Start the authenticated server
exec $PYTHON_CMD enactai_server_local_auth.py