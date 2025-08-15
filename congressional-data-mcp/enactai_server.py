#!/usr/bin/env python3
"""
EnactAI Data MCP Server
Provides legislative data access for EnactAI platform
"""

import os
import json
import asyncio
import httpx
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# Get API keys from environment
CONGRESS_API_KEY = os.getenv("CONGRESS_GOV_API_KEY", "")
GOVINFO_API_KEY = os.getenv("GOVINFO_API_KEY", "")

# Create server
server = Server("enactai-data")

# HTTP client
client = httpx.AsyncClient(timeout=30.0)

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools."""
    return [
        types.Tool(
            name="get_bill",
            description="Get information about a specific bill",
            inputSchema={
                "type": "object",
                "properties": {
                    "congress": {"type": "integer", "description": "Congress number (e.g., 118)"},
                    "bill_type": {"type": "string", "description": "Bill type (hr, s, hjres, sjres)"},
                    "bill_number": {"type": "integer", "description": "Bill number"}
                },
                "required": ["congress", "bill_type", "bill_number"]
            }
        ),
        types.Tool(
            name="search_bills",
            description="Search for recent bills in Congress",
            inputSchema={
                "type": "object",
                "properties": {
                    "congress": {"type": "integer", "description": "Congress number (e.g., 118)", "default": 118},
                    "limit": {"type": "integer", "description": "Number of results to return", "default": 10}
                }
            }
        ),
        types.Tool(
            name="get_member",
            description="Get information about a member of Congress",
            inputSchema={
                "type": "object",
                "properties": {
                    "bioguide_id": {"type": "string", "description": "Bioguide ID of the member (e.g., 'P000197')"}
                },
                "required": ["bioguide_id"]
            }
        ),
        types.Tool(
            name="search_govinfo",
            description="Search GovInfo for government documents",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "collection": {"type": "string", "description": "Collection to search (BILLS, PLAW, FR, CFR)", "default": ""},
                    "limit": {"type": "integer", "description": "Number of results", "default": 10}
                },
                "required": ["query"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str,
    arguments: dict
) -> list[types.TextContent]:
    """Handle tool execution."""
    
    if name == "get_bill":
        try:
            congress = arguments["congress"]
            bill_type = arguments["bill_type"]
            bill_number = arguments["bill_number"]
            
            # Call Congress.gov API
            url = f"https://api.congress.gov/v3/bill/{congress}/{bill_type}/{bill_number}"
            headers = {"X-Api-Key": CONGRESS_API_KEY}
            params = {"format": "json"}
            
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract key information
            bill_info = data.get("bill", {})
            result = {
                "congress": bill_info.get("congress"),
                "type": bill_info.get("type"),
                "number": bill_info.get("number"),
                "title": bill_info.get("title"),
                "sponsor": bill_info.get("sponsors", [{}])[0].get("fullName") if bill_info.get("sponsors") else None,
                "introduced_date": bill_info.get("introducedDate"),
                "latest_action": bill_info.get("latestAction", {}).get("text"),
                "url": bill_info.get("url")
            }
            
            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
            
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Error fetching bill: {str(e)}"
            )]
    
    elif name == "search_bills":
        try:
            congress = arguments.get("congress", 118)
            limit = arguments.get("limit", 10)
            
            # Get recent bills
            url = f"https://api.congress.gov/v3/bill/{congress}"
            headers = {"X-Api-Key": CONGRESS_API_KEY}
            params = {"format": "json", "limit": limit, "sort": "updateDate+desc"}
            
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            bills = data.get("bills", [])
            
            # Format results
            results = []
            for bill in bills:
                results.append({
                    "congress": bill.get("congress"),
                    "type": bill.get("type"),
                    "number": bill.get("number"),
                    "title": bill.get("title"),
                    "latest_action": bill.get("latestAction", {}).get("text"),
                    "url": bill.get("url")
                })
            
            return [types.TextContent(
                type="text",
                text=json.dumps(results, indent=2)
            )]
            
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Error searching bills: {str(e)}"
            )]
    
    elif name == "get_member":
        try:
            bioguide_id = arguments["bioguide_id"]
            
            # Get member info
            url = f"https://api.congress.gov/v3/member/{bioguide_id}"
            headers = {"X-Api-Key": CONGRESS_API_KEY}
            params = {"format": "json"}
            
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            member = data.get("member", {})
            
            # Format result
            result = {
                "name": member.get("directOrderName"),
                "state": member.get("state"),
                "district": member.get("district"),
                "party": member.get("partyName"),
                "chamber": "House" if member.get("district") else "Senate",
                "bioguide_id": member.get("bioguideId"),
                "official_website": member.get("officialWebsiteUrl"),
                "terms": len(member.get("terms", []))
            }
            
            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
            
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Error fetching member: {str(e)}"
            )]
    
    elif name == "search_govinfo":
        try:
            query = arguments["query"]
            collection = arguments.get("collection", "")
            limit = arguments.get("limit", 10)
            
            # Search GovInfo
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
            results = data.get("results", [])
            
            # Format results
            formatted = []
            for doc in results:
                formatted.append({
                    "title": doc.get("title"),
                    "package_id": doc.get("packageId"),
                    "date": doc.get("dateIssued"),
                    "collection": doc.get("collectionCode"),
                    "pdf_link": doc.get("download", {}).get("pdfLink"),
                    "detail_link": doc.get("detailsLink")
                })
            
            return [types.TextContent(
                type="text",
                text=json.dumps(formatted, indent=2)
            )]
            
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Error searching GovInfo: {str(e)}"
            )]
    
    else:
        return [types.TextContent(
            type="text",
            text=f"Unknown tool: {name}"
        )]

async def run():
    """Run the server."""
    # Run the server using stdin/stdout
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="enactai-data",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(run())