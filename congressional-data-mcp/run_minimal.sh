#!/bin/bash
# Minimal MCP server runner

# Set API keys directly
export CONGRESS_GOV_API_KEY="TrgBSRaXdU2gDqbR1xNxqfKS7NFw5CnsC4Flmzrw"
export GOVINFO_API_KEY="xUks0eY6w8kt2UZ8IacQteHYMXqQBrU5P4d7eWsd"

# Run with Python that has packages
exec /opt/homebrew/bin/python3 /Users/corytitus/Documents/GitHub/congress-mcp/congressional-data-mcp/server_minimal.py