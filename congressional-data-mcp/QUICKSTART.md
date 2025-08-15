# Congressional Data MCP - Quick Start Guide

## 🚀 One Command Setup

```bash
# For Docker testing/deployment:
./quickstart.sh docker

# For Claude Desktop integration:
./quickstart.sh local
```

## ✅ What You Now Have

### Single Optimized Server (`server.py`)
- **Dual Mode Operation**: Runs as MCP server OR Docker service
- **Congress.gov API**: Bills, members, votes, committees
- **GovInfo API**: Public laws, Federal Register, CFR, full documents
- **Smart Caching**: Redis-backed when available, memory fallback
- **Health Monitoring**: Built-in health check and metrics endpoints
- **Rate Limiting**: Respects API quotas automatically

### Clean Architecture
- **One server file**: `server.py` handles everything
- **Docker ready**: Full containerization with docker-compose
- **Claude Desktop ready**: Direct Python execution for MCP
- **Cloud ready**: Deployable to any container platform

## 📊 Available Tools

1. **Congress.gov Tools**
   - `get_bills` - Search and filter bills
   - `get_bill_details` - Full bill information with text
   - `get_members` - Member information
   - `get_votes` - Voting records
   - `get_committees` - Committee data

2. **GovInfo Tools**
   - `govinfo_search` - Full-text document search
   - `govinfo_get_package` - Document packages with content
   - `get_public_laws` - Enacted laws
   - `get_federal_register` - Federal Register documents
   - `get_cfr` - Code of Federal Regulations

3. **Combined Tools**
   - `track_legislation` - Track bills from introduction to law

## 🔧 Management Commands

```bash
# View logs
docker-compose logs -f congressional-mcp

# Stop services
docker-compose down

# Restart
docker-compose restart

# Check status
docker-compose ps
```

## 🌐 Endpoints

- **Health Check**: http://localhost:8081/health
- **Prometheus Metrics**: http://localhost:9090

## 🔑 Environment Variables

Your API keys are configured in `.env`:
- `CONGRESS_GOV_API_KEY` - Your Congress.gov key
- `GOVINFO_API_KEY` - Your GovInfo key

## 💡 Usage Tips

1. **For Claude Desktop**: Your config at `~/Library/Application Support/Claude/claude_desktop_config.json` already has this server as `congressional-data-enhanced`

2. **For Docker**: Container runs with health checks and stays alive for monitoring

3. **For Cloud**: Push the Docker image to any registry and deploy

## 🎯 Next Steps

- **Test an API call**: Try searching for recent bills
- **Monitor performance**: Check the metrics endpoint
- **Deploy to cloud**: Use the Docker image with any cloud provider

Your MCP server is now running cleanly with a single, optimized codebase!