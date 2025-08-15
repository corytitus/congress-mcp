#!/bin/bash

# EnactAI MCP Server Launcher with Stateless Authentication
# This script starts the stateless MCP server for Claude Desktop

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

# Set token secret key (must match the one used to create tokens)
if [ -z "$TOKEN_SECRET_KEY" ]; then
    if [ -f .env ] && grep -q TOKEN_SECRET_KEY .env; then
        export TOKEN_SECRET_KEY=$(grep TOKEN_SECRET_KEY .env | cut -d'=' -f2)
    else
        echo "⚠️  WARNING: TOKEN_SECRET_KEY not found in .env file" >&2
        echo "   Tokens may not validate correctly" >&2
    fi
fi

echo "🔐 Starting EnactAI MCP Server (Stateless Authentication)" >&2
echo "======================================================" >&2
echo "" >&2
echo "✅ Token validation on every request" >&2
echo "✅ No session state issues" >&2
echo "✅ Works reliably with MCP protocol" >&2
echo "" >&2

# Check if tokens exist
token_count=$($PYTHON_CMD -c "from token_manager import TokenManager; m = TokenManager(); print(len(m.list_tokens()))" 2>/dev/null || echo "0")

if [ "$token_count" = "0" ]; then
    echo "⚠️  No API tokens found!" >&2
    echo "" >&2
    echo "Creating a default token..." >&2
    output=$($PYTHON_CMD token_manager.py create "Claude Desktop" --permissions admin 2>&1)
    token=$(echo "$output" | grep "Token: " | cut -d' ' -f2)
    
    if [ -n "$token" ]; then
        echo "" >&2
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
        echo "Your token: $token" >&2
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
        echo "" >&2
    fi
else
    echo "✅ Found $token_count existing token(s)" >&2
fi

echo "Starting stateless server..." >&2
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2

# Start the stateless server
exec $PYTHON_CMD enactai_server_stateless.py