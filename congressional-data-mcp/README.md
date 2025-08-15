# Congressional Data MCP Server

A comprehensive Model Context Protocol (MCP) server that provides unified access to both Congress.gov and GovInfo APIs, containerized with Docker for easy self-hosting.

## Features

- **Unified Interface**: Single MCP interface for both Congress.gov and GovInfo data
- **Comprehensive Coverage**: Access to bills, members, votes, committees, public laws, Federal Register, CFR, and more
- **Docker Containerized**: Easy deployment with Docker and docker-compose
- **Built-in Caching**: Redis-backed caching for improved performance
- **Rate Limiting**: Configurable rate limits to respect API quotas
- **Health Monitoring**: Built-in health checks and optional Prometheus metrics
- **Async Support**: Fully asynchronous implementation for better performance

## Prerequisites

- Docker and Docker Compose
- Congress.gov API key ([Sign up here](https://api.congress.gov/sign-up/))
- GovInfo API key ([Sign up here](https://api.data.gov/signup/))
- MCP-compatible client (Claude Desktop, Claude Code, or custom implementation)

## Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/congressional-data-mcp.git
   cd congressional-data-mcp
   ```

2. **Configure environment**:
   ```bash
   cp .env.template .env
   # Edit .env and add your API keys
   ```

3. **Build and run with Docker**:
   ```bash
   docker-compose up -d
   ```

4. **Configure your MCP client**:
   
   For Claude Desktop, add to `claude_desktop_config.json`:
   ```json
   {
     "mcpServers": {
       "congressional-data": {
         "command": "docker",
         "args": ["exec", "-i", "congressional-data-mcp", "python", "server.py"]
       }
     }
   }
   ```

### Alternative Installation Methods

- **🏠 Synology NAS**: See [SYNOLOGY_SETUP.md](SYNOLOGY_SETUP.md) for detailed NAS installation
- **💻 Windows**: Use `startup.bat` instead of `startup.sh`
- **🐳 Minimal Setup**: Use `docker-compose-simple.yml` for resource-constrained environments

## Available Tools

### Congress.gov Tools

- **get_bills**: Search and filter congressional bills
- **get_bill_details**: Get comprehensive bill information including text, actions, and cosponsors
- **get_members**: Search for current and historical members of Congress
- **get_votes**: Access House and Senate voting records
- **get_committees**: Get committee information and activities

### GovInfo Tools

- **govinfo_search**: Full-text search across GovInfo collections
- **govinfo_get_package**: Retrieve detailed package information with content
- **govinfo_get_collection**: List packages in specific collections
- **govinfo_get_related**: Find related documents
- **get_public_laws**: Access enacted public laws
- **get_federal_register**: Search Federal Register documents
- **get_cfr**: Access Code of Federal Regulations

### Combined Tools

- **track_legislation**: Track a bill from introduction through enactment

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CONGRESS_GOV_API_KEY` | Congress.gov API key | Required |
| `GOVINFO_API_KEY` | GovInfo API key | Required |
| `CACHE_TTL` | Cache time-to-live in seconds | 3600 |
| `CACHE_SIZE` | Maximum cached items | 1000 |
| `RATE_LIMIT_CONGRESS` | Congress API requests/minute | 100 |
| `RATE_LIMIT_GOVINFO` | GovInfo API requests/minute | 100 |

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
