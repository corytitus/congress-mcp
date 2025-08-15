#!/bin/bash
# Run MCP server with correct Python and environment

# Set Python path (where we installed the packages)
export PATH="/opt/homebrew/bin:$PATH"

# Set environment variables from .env
source /Users/corytitus/Documents/GitHub/congress-mcp/congressional-data-mcp/.env

# Export them for Python
export CONGRESS_GOV_API_KEY
export GOVINFO_API_KEY
export DOCKER_MODE=false
export ENABLE_CACHING=false

# Run the server
exec /opt/homebrew/bin/python3 /Users/corytitus/Documents/GitHub/congress-mcp/congressional-data-mcp/server.py