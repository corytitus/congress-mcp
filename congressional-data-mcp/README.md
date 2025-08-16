# Congressional Data MCP Server

A comprehensive Model Context Protocol (MCP) server that provides unified access to both Congress.gov and GovInfo APIs. Features multiple server implementations including a stateless authentication system for secure deployments and local development servers for Claude Desktop integration.

## Features

- **Multiple Server Implementations**: Stateless, enhanced local, and remote cloud-ready servers
- **Stateless Authentication**: Token-based authentication system for secure deployments
- **Unified Interface**: Single MCP interface for both Congress.gov and GovInfo data
- **Document Storage**: SQLite-based document storage for legislative documents and educational content
- **Related Bills Analysis**: Cross-referencing and relationship mapping between legislative items
- **Comprehensive Coverage**: Access to bills, members, votes, committees, public laws, Federal Register, CFR, and more
- **Built-in Caching**: In-memory caching with TTL for improved performance
- **Async Support**: Fully asynchronous implementation for better performance

## Prerequisites

- Python 3.8+ (for local development)
- Docker and Docker Compose (for containerized deployment)
- Congress.gov API key ([Sign up here](https://api.congress.gov/sign-up/))
- GovInfo API key ([Sign up here](https://api.data.gov/signup/))
- MCP-compatible client (Claude Desktop, Claude Code, or custom implementation)

## Quick Start

### Option 1: Local Development (Recommended for Claude Desktop)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/congressional-data-mcp.git
   cd congressional-data-mcp
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   export CONGRESS_GOV_API_KEY=your_congress_api_key
   export GOVINFO_API_KEY=your_govinfo_api_key
   ```

4. **Configure Claude Desktop**:
   
   Add to `~/.claude/claude_desktop_config.json`:
   ```json
   {
     "mcpServers": {
       "congressional-data": {
         "command": "/path/to/congressional-data-mcp/run_enactai.sh"
       }
     }
   }
   ```

### Option 2: Stateless Server (Recommended for Production)

1. **Run the stateless server**:
   ```bash
   ./run_stateless.sh
   ```

2. **Configure with authentication**:
   ```bash
   export REQUIRE_AUTH=true
   # Use token_cli.py to manage authentication tokens
   ```

### Option 3: Docker Deployment

1. **Configure environment**:
   ```bash
   cp .env.template .env
   # Edit .env and add your API keys
   ```

2. **Build and run with Docker**:
   ```bash
   docker-compose up -d
   ```

### Alternative Installation Methods

- **🏠 Synology NAS**: See [SYNOLOGY_SETUP.md](SYNOLOGY_SETUP.md) for detailed NAS installation
- **💻 Windows**: Use `startup.bat` instead of `startup.sh`
- **🐳 Minimal Setup**: Use `docker-compose-simple.yml` for resource-constrained environments

## Available Tools

### Core Legislative Tools

- **search_bills**: Search congressional bills with advanced filtering
- **get_bill**: Get comprehensive information about a specific bill
- **get_related_bills**: Find bills related to a specific bill (similar bills, procedurally-related bills, etc.)
- **get_member**: Get detailed information about a member of Congress
- **get_votes**: Access House and Senate voting records
- **get_committee**: Get information about congressional committees

### Document Management Tools

- **store_document**: Store legislative documents and educational content
- **search_documents**: Search stored documents by content, title, or tags
- **get_document**: Retrieve a specific stored document
- **list_documents**: List all stored documents with metadata

### Authentication Tools (Stateless Server)

- **authenticate**: Validate API tokens for secure access

### Educational Tools

- **learn_congress**: Interactive lessons about how Congress works
- **explain_bill_process**: Learn about the legislative process
- **get_civics_info**: Access civics education resources

## Authentication Guide

### For Stateless Server (Production)

The stateless server supports token-based authentication for secure deployments:

1. **Enable authentication**:
   ```bash
   export REQUIRE_AUTH=true
   ```

2. **Create tokens**:
   ```bash
   python token_cli.py create --name "my-token" --description "Token for production use"
   ```

3. **Use tokens in API calls**:
   Include the token in each tool call as a parameter.

4. **Manage tokens**:
   ```bash
   python token_cli.py list                # List all tokens
   python token_cli.py revoke <token_id>   # Revoke a token
   ```

For detailed authentication setup, see [STATELESS_AUTH_GUIDE.md](STATELESS_AUTH_GUIDE.md).

### For Local Development

Local development servers (enhanced) don't require authentication by default. Simply set your API keys:

```bash
export CONGRESS_GOV_API_KEY=your_key
export GOVINFO_API_KEY=your_key
```

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CONGRESS_GOV_API_KEY` | Congress.gov API key | Required |
| `GOVINFO_API_KEY` | GovInfo API key | Required |
| `REQUIRE_AUTH` | Enable token authentication (stateless server) | true |
| `CACHE_TTL` | Cache time-to-live in seconds | 300 |

### Docker Compose Services

- **congressional-mcp**: Main MCP server
- **redis**: Optional caching layer for better performance
- **prometheus**: Optional metrics collection for monitoring

## Usage Examples

### Search for Recent Bills
```python
{
  "tool": "get_bills",
  "arguments": {
    "congress": 118,
    "from_datetime": "2024-01-01T00:00:00Z",
    "limit": 10,
    "sort": "updateDate+desc"
  }
}
```

### Get Detailed Bill Information
```python
{
  "tool": "get_bill_details",
  "arguments": {
    "congress": 118,
    "bill_type": "hr",
    "bill_number": 1234,
    "include": ["actions", "cosponsors", "text"]
  }
}
```

### Search Federal Register
```python
{
  "tool": "get_federal_register",
  "arguments": {
    "query": "environmental protection",
    "agency": "EPA",
    "doc_type": "rule",
    "from_date": "2024-01-01"
  }
}
```

### Track Legislation
```python
{
  "tool": "track_legislation",
  "arguments": {
    "congress": 118,
    "bill_type": "s",
    "bill_number": 100
  }
}
```

## Development

### Local Development without Docker

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set environment variables:
   ```bash
   export CONGRESS_GOV_API_KEY=your-key
   export GOVINFO_API_KEY=your-key
   ```

3. Run the server:
   ```bash
   python server.py
   ```

### Running Tests

```bash
pytest tests/ -v --cov=server
```

### Building Custom Docker Image

```bash
docker build -t congressional-data-mcp:custom .
```

## Monitoring

If Prometheus monitoring is enabled, metrics are available at:
- Server metrics: `http://localhost:8080/metrics`
- Prometheus UI: `http://localhost:9090`

## Troubleshooting

### Common Issues

1. **API Key Errors**: Ensure your API keys are correctly set in the `.env` file
2. **Rate Limiting**: Adjust `RATE_LIMIT_*` variables if you're hitting limits
3. **Connection Issues**: Check Docker logs: `docker-compose logs congressional-mcp`
4. **Cache Issues**: Clear Redis cache: `docker-compose exec redis redis-cli FLUSHALL`

### Debug Mode

Enable detailed logging:
```bash
MCP_LOG_LEVEL=DEBUG docker-compose up
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

- Report issues on GitHub
- Check Congress.gov API documentation: https://api.congress.gov
- Check GovInfo API documentation: https://api.govinfo.gov/docs

## Acknowledgments

- Based on the original Congress MCP by AshwinSundar
- Congress.gov API by Library of Congress
- GovInfo API by U.S. Government Publishing Office
