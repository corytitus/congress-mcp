# Congressional Data MCP Server

A Model Context Protocol (MCP) server providing authenticated access to U.S. Congressional data via Congress.gov and GovInfo.gov APIs.

## Features

- 🔐 **Token-based authentication** - Secure API access with permission levels
- 📊 **15+ Congressional data tools** - Bills, members, votes, committees, and more
- 🚀 **Local & cloud ready** - Works with Claude Desktop locally or deploy to cloud
- 📈 **Usage tracking** - Monitor API usage and token statistics
- ⚡ **Smart caching** - Reduces API calls with intelligent caching

## Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/congress-mcp.git
cd congress-mcp
```

### 2. Install dependencies
```bash
pip install mcp httpx
```

### 3. Set up authentication
```bash
cd congressional-data-mcp
./setup_auth.sh
```

This creates your first API token. Save it securely!

### 4. Configure Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "enactai-data-auth": {
      "command": "/path/to/congressional-data-mcp/run_auth.sh"
    }
  }
}
```

### 5. Authenticate in Claude

Start a new conversation and authenticate:
```
Use the authenticate tool with token: [your-token-here]
```

## Available Tools

- `authenticate` - Authenticate with API token
- `search_bills` - Search congressional bills
- `get_bill` - Get detailed bill information
- `get_member` - Get member of Congress details
- `get_votes` - Get recent votes
- `get_committee` - Get committee information
- `search_amendments` - Search bill amendments
- `search_govinfo` - Search government documents
- `get_public_law` - Get public law information
- `get_congressional_record` - Search floor proceedings
- `get_federal_register` - Search rules and notices
- `calculate_legislative_stats` - Calculate legislative statistics
- `get_congress_overview` - Educational overview of Congress
- `get_legislative_process` - Learn how bills become laws

## Token Management

### Create tokens
```bash
python token_manager.py create "Token Name" --permissions standard
```

### List tokens
```bash
python token_manager.py list
```

### View usage
```bash
python token_manager.py stats [token_id]
```

### Revoke tokens
```bash
python token_manager.py revoke [token_id]
```

## Permission Levels

- **read_only** - Read access to data tools
- **standard** - Read and standard operations
- **admin** - Full access to all tools

## API Keys (Optional)

For better rate limits, get free API keys:
- [Congress.gov API](https://api.congress.gov/sign-up/)
- [GovInfo.gov API](https://api.govinfo.gov/docs/)

Add to `.env`:
```
CONGRESS_GOV_API_KEY=your_key_here
GOVINFO_API_KEY=your_key_here
```

## Project Structure

```
congressional-data-mcp/
├── enactai_server_local_auth.py  # Authenticated MCP server
├── token_manager.py               # Token management system
├── run_auth.sh                    # Server startup script
├── setup_auth.sh                  # Initial setup script
└── tokens.db                      # Token database (auto-created)
```

## Security

- Tokens are hashed with HMAC-SHA256
- No plaintext tokens stored
- Automatic token expiration support
- Usage tracking and audit logs
- Rate limiting via caching

## Support

For issues or questions, please open an issue on GitHub.

## License

MIT License - See LICENSE file for details