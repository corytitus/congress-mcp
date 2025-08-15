#!/usr/bin/env python3
"""
Congressional Data MCP Server - Simplified following official quickstart
"""

import os
import sys
import json
import asyncio
from typing import Any

import httpx
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# API Configuration
CONGRESS_API_KEY = os.getenv("CONGRESS_GOV_API_KEY")
GOVINFO_API_KEY = os.getenv("GOVINFO_API_KEY")

# Create server instance
server = Server("congressional-data")

# Create HTTP client
client = httpx.AsyncClient(timeout=30.0)

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="search_bills",
            description="Search for congressional bills",
            inputSchema={
                "type": "object",
                "properties": {
                    "congress": {
                        "type": "integer",
                        "description": "Congress number (e.g., 118)"
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results",
                        "default": 10
                    }
                }
            }
        ),
        Tool(
            name="get_bill",
            description="Get detailed information about a specific bill",
            inputSchema={
                "type": "object",
                "required": ["congress", "bill_type", "bill_number"],
                "properties": {
                    "congress": {
                        "type": "integer",
                        "description": "Congress number"
                    },
                    "bill_type": {
                        "type": "string",
                        "description": "Bill type (hr, s, hjres, sjres)"
                    },
                    "bill_number": {
                        "type": "integer",
                        "description": "Bill number"
                    }
                }
            }
        ),
        Tool(
            name="search_govinfo",
            description="Search GovInfo for government documents",
            inputSchema={
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "collection": {
                        "type": "string",
                        "description": "Collection (BILLS, PLAW, FR, CFR)"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10
                    }
                }
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""
    try:
        if name == "search_bills":
            # Search Congress.gov for bills
            congress = arguments.get("congress", 118)
            limit = arguments.get("limit", 10)
            
            url = f"https://api.congress.gov/v3/bill/{congress}"
            headers = {"X-Api-Key": CONGRESS_API_KEY}
            params = {"format": "json", "limit": limit}
            
            if "query" in arguments:
                # Note: Congress.gov API doesn't have direct query param, 
                # this would need to be implemented with filtering
                pass
            
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            return [TextContent(
                type="text",
                text=json.dumps(data, indent=2)
            )]
        
        elif name == "get_bill":
            # Get specific bill details
            congress = arguments["congress"]
            bill_type = arguments["bill_type"]
            bill_number = arguments["bill_number"]
            
            url = f"https://api.congress.gov/v3/bill/{congress}/{bill_type}/{bill_number}"
            headers = {"X-Api-Key": CONGRESS_API_KEY}
            params = {"format": "json"}
            
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            return [TextContent(
                type="text",
                text=json.dumps(data, indent=2)
            )]
        
        elif name == "search_govinfo":
            # Search GovInfo
            query = arguments["query"]
            collection = arguments.get("collection", "")
            limit = arguments.get("limit", 10)
            
            url = "https://api.govinfo.gov/search"
            params = {
                "api_key": GOVINFO_API_KEY,
                "query": query,
                "pageSize": limit
            }
            
            if collection:
                params["collection"] = collection
            
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return [TextContent(
                type="text",
                text=json.dumps(data, indent=2)
            )]
        
        else:
            return [TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]
    
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]

async def main():
    """Run the server using stdio transport"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="congressional-data",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    import sys
    asyncio.run(main())