#!/bin/bash
# Congressional Data MCP - Quick Start Script

echo "🏛️ Congressional Data MCP Server"
echo "================================="

# Check if running locally or in Docker
if [ "$1" = "docker" ]; then
    echo "Starting in Docker mode..."
    docker-compose up -d --build
    echo "✅ Server running at http://localhost:8081/health"
    echo "View logs: docker-compose logs -f congressional-mcp"
elif [ "$1" = "local" ]; then
    echo "Starting in local mode for Claude Desktop..."
    source .env
    export CONGRESS_GOV_API_KEY
    export GOVINFO_API_KEY
    export DOCKER_MODE=false
    python3 server.py
else
    echo "Usage: ./quickstart.sh [docker|local]"
    echo ""
    echo "  docker - Run with Docker for testing/deployment"
    echo "  local  - Run locally for Claude Desktop integration"
    echo ""
    echo "Current status:"
    docker-compose ps 2>/dev/null || echo "  Docker containers not running"
fi