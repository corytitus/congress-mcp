# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **EnactAI Data MCP Server** - a Model Context Protocol (MCP) server that provides authoritative legislative data from Congress.gov and GovInfo.gov APIs. The project supports both local Claude Desktop integration and remote cloud deployment for use with custom connectors across different LLM platforms.

## Architecture

### Core Server Implementations

- **`enactai_server_enhanced.py`** - Primary local MCP server with 14 comprehensive tools, in-memory caching, and stdio transport
- **`enactai_server_remote.py`** - Cloud-ready FastAPI server with SSE transport for remote connections
- **`server.py`** - Legacy comprehensive server with Redis/Prometheus support (original implementation)

### Key Architectural Patterns

**MCP Protocol Implementation:**
- Uses `mcp.server.Server` for protocol handling
- Tools are registered via `@server.list_tools()` and `@server.call_tool()` decorators
- Communication via stdio (local) or SSE (remote) transport

**Dual Data Source Integration:**
- **Congress.gov API** - Legislative data (bills, members, votes, committees)
- **GovInfo.gov API** - Official documents (laws, Federal Register, CFR)
- All responses include proper source citations via `format_source()` function

**Caching Strategy:**
- Enhanced server: In-memory cache with TTL (5 minutes default)
- Legacy server: Optional Redis integration
- Cache keys generated via MD5 hash of tool name + arguments

**Error Handling:**
- All API calls wrapped in try/catch with user-friendly error messages
- HTTP client configured with retries and connection pooling
- Rate limiting awareness built into caching strategy

## Common Commands

### Local Development & Testing

```bash
# Run enhanced local server (current production)
./run_enactai.sh

# Run remote server locally with Docker
docker-compose -f docker-compose.remote.yml up -d

# Test remote server functionality  
SERVER_URL=http://localhost:8082 python3 test_remote.py

# Test local MCP integration
python3 test_mcp.py

# Run comprehensive tests
pytest tests/ -v --cov=server
```

### Docker Operations

```bash
# Build and run main server with Redis/Prometheus
docker-compose up -d

# Build remote server only
docker-compose -f docker-compose.remote.yml build

# View server logs
docker logs congressional-data-mcp
```

### Environment Setup

Required environment variables in `.env`:
```bash
CONGRESS_GOV_API_KEY=your_key_from_api.congress.gov
GOVINFO_API_KEY=your_key_from_api.govinfo.gov
ENACTAI_API_TOKEN=optional_bearer_token_for_remote
```

## Tool Implementation Patterns

### Standard Tool Structure
Each tool follows this pattern:
1. Extract and validate arguments
2. Check cache for existing response
3. Make API call with proper headers and error handling
4. Format response data for consistency
5. Cache response and return with source citation

### API Integration Conventions
- **Congress.gov**: Uses `X-Api-Key` header, 1000 req/hour limit
- **GovInfo.gov**: Uses `api_key` query parameter, varying limits
- All HTTP calls use shared `httpx.AsyncClient` with 30s timeout
- Follow redirects and handle rate limiting gracefully

### Response Format Standards
- JSON responses with consistent field naming
- Include source citations in all responses
- Provide user-friendly error messages
- Educational tools include structured learning content

## Claude Desktop Integration

The server integrates with Claude Desktop via the configuration in `~/.claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "enactai-data": {
      "command": "/path/to/run_enactai.sh"
    }
  }
}
```

The `run_enactai.sh` script sets API keys and runs the enhanced server with proper Python environment.

## Remote Deployment Architecture

### Cloud Deployment Pattern
- **FastAPI + SSE** transport for remote connections
- **Bearer token authentication** for public deployments
- **Health check endpoints** at `/health` for load balancer integration
- **CORS configuration** for cross-origin requests

### Multi-Platform Support
- **Railway** - Primary recommendation with railway.json config
- **Render** - Alternative with render.yaml config  
- **Digital Ocean** - App Platform support
- **Generic Docker** - Works on any container platform

## Development Workflow

### Adding New Tools
1. Add tool definition to `handle_list_tools()` with proper JSON schema
2. Implement handler in `handle_call_tool()` following existing patterns
3. Add proper caching and error handling
4. Update both enhanced and remote servers for consistency
5. Test with both local and remote configurations

### API Changes
- Maintain backwards compatibility in tool signatures
- Update cache keys if argument structure changes
- Test against rate limits of external APIs
- Document new features in appropriate README files

### Configuration Management
- Environment variables for all sensitive data
- Default values for optional configuration
- Docker compose files for different deployment scenarios
- Separate requirements files for local vs remote deployments

## Data Sources & API Limits

- **Congress.gov**: 1000 requests/hour - cache aggressively
- **GovInfo.gov**: Rate limits vary by endpoint - respect API guidelines
- Both APIs require registration and provide free access
- Server implements respectful caching to minimize API usage