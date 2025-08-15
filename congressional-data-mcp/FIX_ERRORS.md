# 🔧 Fixing Common Errors

## If Claude Desktop shows "Server not responding" or similar:

### 1. Test the server directly:
```bash
cd /Users/corytitus/Documents/GitHub/congress-mcp/congressional-data-mcp
python3 enactai_server_local_auth.py
```
You should see output like:
```
🔐 Authentication: ENABLED
📊 EnactAI Data MCP Server (Local with Auth)
```

If you see errors, let me know what they are.

### 2. Check Python version:
```bash
python3 --version
```
Should be 3.7 or higher.

### 3. Install missing dependencies:
```bash
pip3 install mcp httpx
```

### 4. Try without authentication first:
```bash
# Test without auth requirement
REQUIRE_AUTH=false python3 enactai_server_local_auth.py
```

### 5. Check if regular server still works:
```bash
./run_enactai.sh
```

## If authentication fails in Claude:

### 1. Verify your token:
```bash
python3 -c "
from token_manager import TokenManager
m = TokenManager()
result = m.validate_token('enact_D7WFVT_HPj7Y4nSCJf9v9wlAMZAlgEKkmoMp2a3Gcn8')
print('Token valid' if result else 'Token invalid')
"
```

### 2. Create a fresh token:
```bash
python3 token_manager.py create "Test Token" --permissions admin
```

### 3. Test authentication directly:
```bash
python3 -c "
from token_manager import TokenManager
m = TokenManager()
tokens = m.list_tokens()
for t in tokens:
    print(f\"ID: {t['id']}, Name: {t['name']}, Active: {t['active']}\")
"
```

## If Claude Desktop doesn't show the server:

1. **Restart Claude Desktop completely**:
   - Quit Claude Desktop (Cmd+Q on Mac)
   - Wait 5 seconds
   - Open Claude Desktop again

2. **Check the config is valid JSON**:
```bash
python3 -m json.tool "/Users/corytitus/Library/Application Support/Claude/claude_desktop_config.json"
```

3. **Try a minimal test server**:
Create a test script `test_mcp.py`:
```python
#!/usr/bin/env python3
import asyncio
from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio as stdio

server = Server("test-server")

@server.list_tools()
async def handle_list_tools():
    return []

async def main():
    async with stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="test-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
```

Then add to Claude config:
```json
"test-server": {
  "command": "python3",
  "args": ["/path/to/test_mcp.py"]
}
```

## Please share:
1. The exact error message you're seeing
2. Where you see it (Claude Desktop, terminal, etc.)
3. Output of: `python3 enactai_server_local_auth.py`

This will help me provide a specific fix!