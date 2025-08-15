#!/bin/bash
# Congressional Data MCP Server Startup Script

set -e

echo "🏛️ Congressional Data MCP Server Startup"
echo "======================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please copy .env.template to .env and add your API keys."
    exit 1
fi

# Source environment variables
source .env

# Check required API keys
if [ -z "$CONGRESS_GOV_API_KEY" ]; then
    echo "❌ Error: CONGRESS_GOV_API_KEY not set in .env file!"
    exit 1
fi

if [ -z "$GOVINFO_API_KEY" ]; then
    echo "❌ Error: GOVINFO_API_KEY not set in .env file!"
    exit 1
fi

# Check Docker installation
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed!"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: Docker Compose is not installed!"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# Parse command line arguments
COMMAND=${1:-"up"}
DETACH=""
BUILD=""

case "$COMMAND" in
    "up")
        DETACH="-d"
        BUILD="--build"
        ;;
    "up-attached")
        BUILD="--build"
        ;;
    "down")
        echo "📦 Stopping Congressional Data MCP Server..."
        docker-compose down
        exit 0
        ;;
    "logs")
        docker-compose logs -f congressional-mcp
        exit 0
        ;;
    "shell")
        docker-compose exec congressional-mcp /bin/bash
        exit 0
        ;;
    "test")
        echo "🧪 Running tests..."
        docker-compose exec congressional-mcp pytest tests/ -v
        exit 0
        ;;
    "cache-clear")
        echo "🗑️ Clearing cache..."
        docker-compose exec redis redis-cli FLUSHALL
        echo "✅ Cache cleared!"
        exit 0
        ;;
    "status")
        echo "📊 Service Status:"
        docker-compose ps
        exit 0
        ;;
    *)
        echo "Usage: ./startup.sh [command]"
        echo "Commands:"
        echo "  up          - Start services in background (default)"
        echo "  up-attached - Start services in foreground"
        echo "  down        - Stop all services"
        echo "  logs        - View logs"
        echo "  shell       - Open shell in container"
        echo "  test        - Run tests"
        echo "  cache-clear - Clear Redis cache"
        echo "  status      - Show service status"
        exit 1
        ;;
esac

# Build and start services
echo "🔨 Building Docker images..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up $DETACH $BUILD

if [ "$DETACH" = "-d" ]; then
    echo ""
    echo "✅ Congressional Data MCP Server is running!"
    echo ""
    echo "📋 Quick Commands:"
    echo "  View logs:        ./startup.sh logs"
    echo "  Stop services:    ./startup.sh down"
    echo "  Service status:   ./startup.sh status"
    echo "  Clear cache:      ./startup.sh cache-clear"
    echo ""
    echo "🔗 Service URLs:"
    echo "  Health Check:     http://localhost:8080/health"
    echo "  Metrics:          http://localhost:8080/metrics"
    echo "  Prometheus:       http://localhost:9090"
    echo ""
    echo "📚 MCP Configuration:"
    echo "  Add the following to your Claude Desktop config:"
    echo '  {
    "mcpServers": {
      "congressional-data": {
        "command": "docker",
        "args": ["exec", "-i", "congressional-data-mcp", "python", "server.py"]
      }
    }
  }'
fi
