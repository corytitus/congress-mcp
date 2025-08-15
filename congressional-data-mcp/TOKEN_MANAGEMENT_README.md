# EnactAI Token Management System

A comprehensive, production-ready token management system for the EnactAI MCP server that provides secure API authentication, usage tracking, and analytics.

## Features

- **Secure Token Management**: HMAC-SHA256 hashed tokens with configurable prefixes and lengths
- **Granular Permissions**: Read-only, standard, and admin permission levels
- **Rate Limiting**: Configurable rate limits per token with burst allowance
- **Usage Analytics**: Detailed tracking of API usage with response times and error rates
- **IP Whitelisting**: Restrict tokens to specific IP addresses or CIDR blocks
- **Tool Restrictions**: Limit tokens to specific API tools/endpoints
- **Token Rotation**: Secure token rotation with automatic revocation of old tokens
- **Expiration Management**: Automatic cleanup of expired tokens
- **Web Dashboard**: Real-time analytics and token management interface
- **CLI Management**: Command-line interface for all token operations
- **Production Security**: Industry-standard security practices

## Quick Start

### 1. Installation

```bash
# Install required dependencies
pip install -r requirements.remote.txt

# Install additional dependencies for token management
pip install sqlite3 passlib bcrypt
```

### 2. Create Your First Admin Token

```bash
# Create an admin token for system management
python token_cli.py create "Admin Token" --permissions admin --description "System administration"
```

Save the generated token securely - you'll need it for all administrative operations.

### 3. Start the Enhanced Server

```bash
# Start the server with token management
python enactai_server_enhanced_tokens.py
```

### 4. Test Authentication

```bash
# Test token authentication
curl -H "Authorization: Bearer your_token_here" http://localhost:8082/auth/verify
```

## Token Management CLI

The CLI provides complete token management capabilities:

### Creating Tokens

```bash
# Basic token creation
python token_cli.py create "My API Token"

# Advanced token with restrictions
python token_cli.py create "Analytics Token" \
    --permissions read_only \
    --rate-limit 500 \
    --allowed-tools "get_bill,search_bills" \
    --ip-whitelist "192.168.1.0/24,10.0.0.100" \
    --expires-in-days 30 \
    --description "Read-only access for analytics dashboard"
```

### Managing Tokens

```bash
# List all tokens
python token_cli.py list

# Show detailed token information
python token_cli.py show "My API Token"

# Revoke a token
python token_cli.py revoke "token_id_here" --reason "Compromised"

# Rotate a token (create new, revoke old)
python token_cli.py rotate "My API Token"
```

### Analytics and Monitoring

```bash
# View system analytics
python token_cli.py analytics --hours 24

# Clean up expired tokens
python token_cli.py cleanup
```

## Permission Levels

### Read-Only
- Can only access GET endpoints
- Cannot modify system state
- Ideal for monitoring and analytics

### Standard
- Full access to all API tools
- Cannot manage other tokens
- Default permission level

### Admin
- Full system access
- Can create, revoke, and rotate tokens
- Access to analytics dashboard
- Can view all system metrics

## Configuration

The system supports configuration via environment variables and config files.

### Environment Variables

```bash
# Database configuration
export TOKEN_DB_PATH="./data/tokens.db"
export TOKEN_DB_CLEANUP_DAYS=30

# Security configuration
export TOKEN_SECRET_KEY="your-secret-key-here"
export TOKEN_PREFIX="myapi_"
export REQUIRE_HTTPS=true

# Rate limiting
export DEFAULT_RATE_LIMIT=1000
export RATE_LIMIT_WINDOW_HOURS=1

# Server configuration
export PORT=8082
export DEBUG=false

# API keys
export CONGRESS_GOV_API_KEY="your-api-key"
export GOVINFO_API_KEY="your-api-key"

# Analytics
export ANALYTICS_ENABLED=true
export DASHBOARD_PORT=8083
```

### Configuration File

Create `token_config.json`:

```json
{
  "database": {
    "path": "tokens.db",
    "backup_enabled": true,
    "cleanup_days": 30
  },
  "security": {
    "token_prefix": "enact_",
    "token_length": 32,
    "require_https": false
  },
  "rate_limiting": {
    "default_rate_limit": 1000,
    "window_hours": 1
  },
  "analytics": {
    "enabled": true,
    "dashboard_enabled": true,
    "dashboard_port": 8083
  }
}
```

## Analytics Dashboard

Access the web dashboard at `http://localhost:8083` (requires admin token).

### Available Endpoints

- `GET /api/overview` - System overview metrics
- `GET /api/tokens` - List all tokens
- `GET /api/tokens/{token_id}` - Token details
- `GET /api/analytics` - Usage analytics
- `GET /api/security` - Security alerts

### Dashboard Authentication

```bash
curl -H "Authorization: Bearer your_admin_token" \
     http://localhost:8083/api/overview
```

## API Integration

### Using Tokens in Requests

```javascript
// JavaScript example
const response = await fetch('http://localhost:8082/api/get_bill', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer enact_abc123def456...',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    congress: 118,
    bill_type: 'hr',
    bill_number: 1
  })
});
```

```python
# Python example
import httpx

headers = {
    'Authorization': 'Bearer enact_abc123def456...',
    'Content-Type': 'application/json'
}

async with httpx.AsyncClient() as client:
    response = await client.post(
        'http://localhost:8082/api/get_bill',
        headers=headers,
        json={
            'congress': 118,
            'bill_type': 'hr',
            'bill_number': 1
        }
    )
```

```bash
# cURL example
curl -X POST \
  -H "Authorization: Bearer enact_abc123def456..." \
  -H "Content-Type: application/json" \
  -d '{"congress": 118, "bill_type": "hr", "bill_number": 1}' \
  http://localhost:8082/api/get_bill
```

## Security Best Practices

### Token Security
1. **Store tokens securely** - Never commit tokens to version control
2. **Use environment variables** - Store tokens in environment variables or secure vaults
3. **Regular rotation** - Rotate tokens regularly, especially admin tokens
4. **Minimal permissions** - Use the lowest permission level required
5. **IP restrictions** - Limit tokens to known IP addresses when possible

### Network Security
1. **HTTPS in production** - Always use HTTPS in production environments
2. **Firewall rules** - Restrict access to token management endpoints
3. **Rate limiting** - Configure appropriate rate limits for your use case

### Monitoring
1. **Track usage** - Monitor token usage patterns for anomalies
2. **Set up alerts** - Configure alerts for suspicious activity
3. **Regular audits** - Regularly review active tokens and permissions

## Database Schema

The system uses SQLite with the following tables:

### tokens
- `id` - Unique token identifier
- `hashed_token` - HMAC-SHA256 hash of the token
- `name` - Human-readable name
- `permissions` - Permission level (read_only, standard, admin)
- `rate_limit` - Requests per hour limit
- `allowed_tools` - JSON array of allowed tools
- `ip_whitelist` - JSON array of allowed IPs
- `created_at` - Creation timestamp
- `expires_at` - Expiration timestamp (optional)
- `is_active` - Active status
- Usage tracking fields

### token_usage
- `id` - Unique usage record identifier
- `token_id` - Foreign key to tokens table
- `timestamp` - Request timestamp
- `tool_name` - API tool/endpoint used
- `success` - Request success status
- `ip_address` - Client IP address
- `response_time_ms` - Response time in milliseconds
- `error_message` - Error details (if any)

## Troubleshooting

### Common Issues

#### "Invalid token format"
- Check that your token starts with the correct prefix (default: `enact_`)
- Verify the token length and character set

#### "Token not found"
- Ensure the token exists and is active
- Check if the token has been revoked or expired

#### "Rate limit exceeded"
- Token has exceeded its hourly request limit
- Wait for the rate limit window to reset or increase the limit

#### "IP address not in whitelist"
- Your IP address is not in the token's whitelist
- Add your IP to the whitelist or remove IP restrictions

#### "Permission denied"
- Token doesn't have sufficient permissions for the requested operation
- Use a token with higher permissions or request access

### Debug Mode

Enable debug mode for detailed logging:

```bash
export DEBUG=true
python enactai_server_enhanced_tokens.py
```

### Database Issues

Check database permissions and path:

```bash
# Validate configuration
python token_config.py

# Check database integrity
sqlite3 tokens.db ".schema"
```

## Production Deployment

### Environment Setup

```bash
# Production environment variables
export TOKEN_SECRET_KEY="$(openssl rand -base64 32)"
export REQUIRE_HTTPS=true
export DEBUG=false
export TOKEN_DB_PATH="/app/data/tokens.db"
export ANALYTICS_ENABLED=true
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.remote.txt .
RUN pip install -r requirements.remote.txt

COPY . .

ENV TOKEN_DB_PATH=/app/data/tokens.db
ENV PORT=8082
ENV DEBUG=false

VOLUME ["/app/data"]
EXPOSE 8082 8083

CMD ["python", "enactai_server_enhanced_tokens.py"]
```

### Health Checks

```bash
# Server health
curl http://localhost:8082/health

# Authentication health
curl -H "Authorization: Bearer your_token" http://localhost:8082/auth/verify

# Dashboard health
curl http://localhost:8083/health
```

## API Reference

### Authentication Endpoints

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/health` | GET | Health check | No |
| `/auth/verify` | GET | Verify token | Yes |

### Admin Endpoints

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/admin/tokens` | GET | List all tokens | Admin |
| `/admin/analytics` | GET | Usage analytics | Admin |
| `/admin/tokens/{id}/revoke` | POST | Revoke token | Admin |

### MCP Tools

All MCP tools require valid token authentication. See the main server documentation for tool-specific endpoints.

## Support

For issues and questions:

1. Check the troubleshooting section above
2. Validate your configuration with `python token_config.py`
3. Enable debug mode for detailed logging
4. Review token permissions and restrictions

## License

This token management system is part of the EnactAI MCP server project.