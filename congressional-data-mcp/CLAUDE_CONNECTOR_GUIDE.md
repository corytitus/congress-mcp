# Using EnactAI Data with Claude Custom Connectors

## Overview

This guide shows how to deploy the EnactAI Data MCP Server as a custom connector for Claude, making it accessible across different LLM platforms.

## Step 1: Deploy to Cloud

### Option A: Railway (Recommended)

1. **Sign up at Railway.app**
2. **Create new project from GitHub repo**
3. **Set environment variables:**
   ```
   CONGRESS_GOV_API_KEY=your_congress_key
   GOVINFO_API_KEY=your_govinfo_key  
   ENACTAI_API_TOKEN=optional_bearer_token
   PORT=8082
   ```
4. **Deploy** - Railway will provide a URL like: `https://your-app.up.railway.app`

### Option B: Render

1. **Fork this repository on GitHub**
2. **Connect to Render:**
   - Go to https://render.com
   - Click "New +" → "Web Service" 
   - Connect your GitHub repo
3. **Configure:**
   - Build Command: `docker build -f Dockerfile.remote -t enactai-remote .`
   - Start Command: `python enactai_server_remote.py`
   - Add environment variables as above

### Option C: Digital Ocean App Platform

1. **Create app.yaml:**
```yaml
name: enactai-data-mcp
services:
- build_command: docker build -f Dockerfile.remote .
  environment_slug: docker
  github:
    branch: main
    deploy_on_push: true
    repo: your-username/enactai-data-mcp
  http_port: 8082
  instance_count: 1
  instance_size_slug: basic-xxs
  name: web
  routes:
  - path: /
  source_dir: /
  envs:
  - key: CONGRESS_GOV_API_KEY
    scope: RUN_AND_BUILD_TIME
    value: your_key_here
  - key: GOVINFO_API_KEY  
    scope: RUN_AND_BUILD_TIME
    value: your_key_here
```

## Step 2: Configure Claude Desktop

Once deployed, add to your Claude Desktop configuration:

### Method 1: Direct MCP Configuration

**File:** `~/.config/claude-desktop/config.json` (Linux/Mac) or `%APPDATA%\Claude\config.json` (Windows)

```json
{
  "mcpServers": {
    "enactai-data": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/mcp-client", "connect", "https://your-app.railway.app/sse"],
      "env": {
        "ENACTAI_API_TOKEN": "your_token_if_configured"
      }
    }
  }
}
```

### Method 2: Custom Connector (If Available)

```json
{
  "customConnectors": {
    "enactai-data": {
      "name": "EnactAI Legislative Data",
      "description": "Authoritative US legislative data from Congress.gov and GovInfo.gov",
      "url": "https://your-app.railway.app/sse",
      "headers": {
        "Authorization": "Bearer your_token_here"
      }
    }
  }
}
```

## Step 3: Test the Connection

### Using curl:

```bash
# Test health endpoint
curl https://your-app.railway.app/health

# Test SSE connection
curl -N -H "Authorization: Bearer your_token" \
     https://your-app.railway.app/sse
```

### Using the Claude Desktop:

1. Restart Claude Desktop
2. Look for "EnactAI Data" in your available tools
3. Test with queries like:
   - "Get information about HR 1234 from the 118th Congress"
   - "Search for recent infrastructure bills"
   - "Show me voting records for a specific member"

## Available Tools

Once connected, you'll have access to 14 comprehensive tools:

### Legislative Data
- `get_bill` - Get detailed bill information
- `search_bills` - Search legislation with filters  
- `track_bill_progress` - Track bills through the legislative process
- `get_public_law` - Information about enacted laws

### Member Information  
- `get_member` - Details about Congress members
- `search_members` - Find members by state, party, chamber
- `get_member_votes` - Voting history for members

### Committee & Voting
- `get_committee` - Committee information and membership
- `get_vote` - Specific vote details and results

### Government Documents
- `search_govinfo` - Search official government documents
- `get_congressional_record` - Congressional Record search

### Educational & Utilities
- `get_legislative_process` - Learn how bills become laws
- `get_congress_overview` - Current Congress information  
- `get_congress_calendar` - Congressional schedule

## Security & Best Practices

### For Production Deployment:

1. **Set API Token:** Always configure `ENACTAI_API_TOKEN` for public deployments
2. **Use HTTPS:** Ensure your deployment uses SSL/TLS
3. **Configure CORS:** Update CORS settings for your domain
4. **Rate Limiting:** Monitor usage to prevent abuse
5. **API Key Rotation:** Regularly rotate your Congress.gov and GovInfo API keys

### Environment Variables:

```bash
# Required
CONGRESS_GOV_API_KEY=your_key_from_api.congress.gov
GOVINFO_API_KEY=your_key_from_api.govinfo.gov

# Optional but recommended for public deployments  
ENACTAI_API_TOKEN=secure_random_string_for_bearer_auth
PORT=8082

# Optional
LOG_LEVEL=INFO
CORS_ORIGINS=*
```

## Troubleshooting

### Common Issues:

1. **"Server not found"** - Check your deployed URL is correct
2. **"Authentication failed"** - Verify your bearer token matches
3. **"Rate limited"** - Check your API key quotas at congress.gov/govinfo.gov
4. **"Tools not appearing"** - Restart Claude Desktop after config changes

### Logs:
Check your deployment platform's logs:
- Railway: `railway logs`  
- Render: View logs in dashboard
- Digital Ocean: `doctl apps logs <app-id>`

### Health Check:
Your deployed server includes a health endpoint at `/health` that returns:
```json
{
  "status": "healthy", 
  "service": "enactai-data",
  "version": "2.0.0"
}
```

## API Keys

### Get Congress.gov API Key:
1. Visit https://api.congress.gov/sign-up/
2. Register with your email
3. API key will be emailed to you
4. Rate limit: 1000 requests/hour

### Get GovInfo API Key:  
1. Visit https://api.govinfo.gov/docs/
2. Click "Sign Up for API Key"
3. Complete the registration form
4. API key provided immediately
5. No explicit rate limits documented

## Support

- **Documentation:** [Model Context Protocol](https://modelcontextprotocol.io)
- **Issues:** [GitHub Issues](https://github.com/your-repo/issues) 
- **Congress.gov API:** [Documentation](https://api.congress.gov/)
- **GovInfo API:** [Documentation](https://api.govinfo.gov/docs/)

## Data Sources & Citations

All data includes proper source citations:
- **Congress.gov** - Library of Congress legislative data
- **GovInfo.gov** - Government Publishing Office documents
- **EnactAI** - Calculated fields and educational content

This ensures transparency and allows users to verify information from authoritative government sources.