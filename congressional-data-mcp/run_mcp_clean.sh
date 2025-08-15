#!/bin/bash
# Clean MCP server runner - no stdout pollution

# Load environment
source /Users/corytitus/Documents/GitHub/congress-mcp/congressional-data-mcp/.env

# Export for Python
export CONGRESS_GOV_API_KEY
export GOVINFO_API_KEY
export DOCKER_MODE=false
export ENABLE_CACHING=false
export ENABLE_METRICS=false

# Run with homebrew Python (has packages installed)
exec /opt/homebrew/bin/python3 /Users/corytitus/Documents/GitHub/congress-mcp/congressional-data-mcp/server.py 2>/dev/null