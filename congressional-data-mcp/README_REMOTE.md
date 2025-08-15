# EnactAI Data MCP Server - Remote Deployment

## Overview

The EnactAI Data MCP Server provides authoritative legislative data from Congress.gov and GovInfo.gov through the Model Context Protocol (MCP). This remote version supports Server-Sent Events (SSE) transport for cloud deployment and can be used with Claude's custom connectors and other LLM platforms.

## Features

### 14 Comprehensive Tools
- **Bill Tracking**: Get details, search, and track progress of legislation
- **Member Information**: Search and retrieve information about Congress members
- **Committee Data**: Access committee information and membership
- **Voting Records**: Retrieve vote details and member voting history
- **Government Documents**: Search GovInfo for laws, regulations, and reports
- **Educational Resources**: Learn about the legislative process
- **Congress Overview**: Get current Congress leadership and statistics

### Data Sources
All data is sourced from official government APIs:
- **Library of Congress** (congress.gov) - Legislative data
- **Government Publishing Office** (govinfo.gov) - Official documents

## Quick Deploy Options

### Railway (Recommended)
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/deploy?template=https://github.com/yourusername/enactai-data-mcp)

1. Click the button above
2. Add your API keys as environment variables:
   - `CONGRESS_GOV_API_KEY`
   - `GOVINFO_API_KEY`
3. Deploy!

### Render
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/yourusername/enactai-data-mcp)

### Manual Docker Deployment

```bash
# Build the image
docker build -f Dockerfile.remote -t enactai-data-mcp .

# Run locally
docker run -p 8080:8080 \
  -e CONGRESS_GOV_API_KEY="your_key" \
  -e GOVINFO_API_KEY="your_key" \
  -e ENACTAI_API_TOKEN="optional_bearer_token" \
  enactai-data-mcp
```

## Using with Claude Desktop

### As a Custom Connector

1. Deploy the server to a public URL (e.g., `https://your-app.railway.app`)
2. In Claude Desktop, go to Settings → Connectors
3. Add a new custom connector:
   - Name: `EnactAI Data`
   - URL: `https://your-app.railway.app/sse`
   - Authentication: Bearer token (if configured)

### Configuration Example

```json
{
  "customConnectors": {
    "enactai-data": {
      "url": "https://your-app.railway.app/sse",
      "headers": {
        "Authorization": "Bearer your_token_here"
      }
    }
  }
}
```

## API Endpoints

- `GET /health` - Health check endpoint
- `GET /sse` - SSE endpoint for MCP protocol
- `GET /openapi.json` - OpenAPI schema

## Authentication

The server supports optional Bearer token authentication:
1. Set `ENACTAI_API_TOKEN` environment variable
2. Include in requests: `Authorization: Bearer <token>`

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `CONGRESS_GOV_API_KEY` | API key from api.congress.gov | Yes |
| `GOVINFO_API_KEY` | API key from api.govinfo.gov | Yes |
| `ENACTAI_API_TOKEN` | Bearer token for authentication | No |
| `PORT` | Server port (default: 8080) | No |

## Getting API Keys

1. **Congress.gov API**: Register at https://api.congress.gov/sign-up/
2. **GovInfo API**: Register at https://api.govinfo.gov/docs/

## Rate Limits

- Congress.gov: 1000 requests per hour
- GovInfo.gov: Varies by endpoint
- Server implements 5-minute caching to reduce API calls

## Security Considerations

- Always use HTTPS in production
- Configure CORS appropriately for your use case
- Use authentication tokens for public deployments
- Rotate API keys regularly
- Monitor usage to prevent abuse

## Development

### Local Testing

```bash
# Install dependencies
pip install -r requirements.remote.txt

# Set environment variables
export CONGRESS_GOV_API_KEY="your_key"
export GOVINFO_API_KEY="your_key"

# Run the server
python enactai_server_remote.py
```

### Testing with curl

```bash
# Health check
curl http://localhost:8080/health

# Test SSE connection
curl -N http://localhost:8080/sse \
  -H "Authorization: Bearer your_token"
```

## Support

For issues or questions:
- GitHub Issues: [Create an issue](https://github.com/yourusername/enactai-data-mcp/issues)
- Documentation: [MCP Protocol](https://modelcontextprotocol.io)

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Data provided by Library of Congress and Government Publishing Office
- Built with the Model Context Protocol by Anthropic
- Powered by FastAPI and httpx