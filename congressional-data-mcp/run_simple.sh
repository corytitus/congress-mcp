#!/bin/bash
# Run simplified MCP server

# Load environment
source /Users/corytitus/Documents/GitHub/congress-mcp/congressional-data-mcp/.env

# Export for Python
export CONGRESS_GOV_API_KEY
export GOVINFO_API_KEY

# Run with correct Python
exec /opt/homebrew/bin/python3 /Users/corytitus/Documents/GitHub/congress-mcp/congressional-data-mcp/server_simple.py