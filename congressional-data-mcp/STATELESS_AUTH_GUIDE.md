# 🔐 Stateless Authentication Guide

## The Problem with the Original Server

The original `enactai-data-auth` server had a critical issue:
- Authentication was stored in memory (`current_token_info`)
- MCP servers are stateless - each tool call is independent
- After authenticating, the next tool call would fail with "not authenticated"

## The Solution: Stateless Authentication

The new `enactai-data-stateless` server:
- ✅ **Includes token in every request** - No session state needed
- ✅ **Validates on every call** - Secure and reliable
- ✅ **Works perfectly with MCP** - Designed for stateless operation
- ✅ **Same token works** - Use your existing token

## How to Use

### 1. Switch to Stateless Server in Claude Desktop

The stateless server is already configured as `enactai-data-stateless`.

**Restart Claude Desktop** to load the new server.

### 2. Authenticate Once

In your conversation with Claude:
```
Use the authenticate tool with token: enact_0Rk5yidWIB36mbmYMO8Fj7PxKPkplcb70TfyQxV9n_g
```

### 3. Token Automatically Included

After authentication, Claude will automatically include your token in every subsequent tool call. You don't need to re-authenticate!

### 4. Use Tools Normally

```
Search for bills about climate change
Get details on HR 1234 from Congress 118
Show member information for bioguide ID P000197
```

## Key Differences

### Old Server (enactai-data-auth)
- ❌ Authenticate → Works once → Next call fails
- ❌ Session state lost between calls
- ❌ Need to re-authenticate constantly

### New Server (enactai-data-stateless)
- ✅ Authenticate once → Works for entire conversation
- ✅ Token included automatically in each request
- ✅ No session state issues

## How It Works

1. **First call**: You authenticate with your token
2. **Server validates**: Token is checked and permissions confirmed
3. **Token passed**: Every subsequent tool call includes the token
4. **Automatic validation**: Server validates token on each request
5. **Seamless experience**: You never need to re-authenticate

## Example Tool Call (Behind the Scenes)

When you ask Claude to "search for climate bills", it actually sends:
```json
{
  "tool": "search_bills",
  "arguments": {
    "token": "enact_0Rk5yidWIB36mbmYMO8Fj7PxKPkplcb70TfyQxV9n_g",
    "query": "climate",
    "congress": 118
  }
}
```

The token is automatically included!

## Troubleshooting

### If authentication fails:
1. Make sure you're using `enactai-data-stateless` server
2. Check the token is correct (copy exactly)
3. Restart Claude Desktop

### To verify it's working:
After authenticating, try multiple tools in succession:
- Get bill information
- Search for members
- Get committee details

All should work without re-authenticating!

## Your Token

```
enact_0Rk5yidWIB36mbmYMO8Fj7PxKPkplcb70TfyQxV9n_g
```

This token has **admin** permissions (full access to all tools).