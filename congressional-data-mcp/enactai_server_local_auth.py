#!/usr/bin/env python3
"""
EnactAI Data MCP Server with Local Authentication
Works like cloud deployment but runs locally with token management
"""

import os
import json
import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import hashlib
import sys
from pathlib import Path

# Add token manager to path
sys.path.append(str(Path(__file__).parent))
from token_manager import TokenManager

# MCP imports
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio as stdio
import mcp.types as types

# Configuration
CONGRESS_API_KEY = os.getenv("CONGRESS_GOV_API_KEY", "")
GOVINFO_API_KEY = os.getenv("GOVINFO_API_KEY", "")
REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "true").lower() == "true"

# Create MCP server
server = Server("enactai-data-local-auth")
token_manager = TokenManager()

# HTTP client for external APIs
client = httpx.AsyncClient(timeout=30.0)

# Cache for API responses (TTL: 5 minutes)
cache: Dict[str, tuple[Any, datetime]] = {}
CACHE_TTL = timedelta(minutes=5)

# Current session token (set during authentication)
current_token_info: Optional[Dict] = None

def get_cache_key(*args) -> str:
    """Generate cache key from arguments."""
    return hashlib.md5(str(args).encode()).hexdigest()

def format_source(source_type: str, identifier: str) -> str:
    """Format source citations for authoritative data."""
    sources = {
        "congress": f"Source: Library of Congress (congress.gov) - {identifier}",
        "govinfo": f"Source: Government Publishing Office (govinfo.gov) - {identifier}",
        "calculation": f"Source: EnactAI Analysis - {identifier}"
    }
    return sources.get(source_type, f"Source: {source_type} - {identifier}")

async def check_permission(tool_name: str) -> bool:
    """Check if current token has permission to use tool"""
    if not REQUIRE_AUTH:
        return True
    
    if not current_token_info:
        return False
    
    permissions = current_token_info.get('permissions', 'read_only')
    
    # Admin can do everything
    if permissions == 'admin':
        return True
    
    # Read-only tools
    read_only_tools = [
        'search_bills', 'get_bill', 'get_member', 'get_committee',
        'get_congress_overview', 'get_legislative_process', 'search_amendments'
    ]
    
    # Standard includes read + some write operations
    if permissions == 'standard':
        return True  # Standard can use all tools
    
    # Read-only can only use read tools
    if permissions == 'read_only':
        return tool_name in read_only_tools
    
    return False

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List all available tools with auth-aware filtering."""
    all_tools = [
        types.Tool(
            name="authenticate",
            description="Authenticate with an API token to access protected tools",
            inputSchema={
                "type": "object",
                "properties": {
                    "token": {"type": "string", "description": "Your API token"}
                },
                "required": ["token"]
            }
        ),
        types.Tool(
            name="get_token_info",
            description="Get information about the current authenticated token",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="search_bills",
            description="Search for congressional bills with advanced filtering",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "congress": {"type": "integer", "description": "Congress number (e.g., 118)"},
                    "chamber": {"type": "string", "enum": ["house", "senate", "both"], "description": "Chamber"},
                    "limit": {"type": "integer", "description": "Maximum results (default 20)"}
                }
            }
        ),
        types.Tool(
            name="get_bill",
            description="Get comprehensive information about a specific bill",
            inputSchema={
                "type": "object",
                "properties": {
                    "congress": {"type": "integer", "description": "Congress number"},
                    "bill_type": {"type": "string", "description": "Bill type (hr, s, hjres, sjres)"},
                    "bill_number": {"type": "integer", "description": "Bill number"}
                },
                "required": ["congress", "bill_type", "bill_number"]
            }
        ),
        types.Tool(
            name="get_member",
            description="Get detailed information about a member of Congress",
            inputSchema={
                "type": "object",
                "properties": {
                    "bioguide_id": {"type": "string", "description": "Member's bioguide ID"}
                },
                "required": ["bioguide_id"]
            }
        ),
        types.Tool(
            name="get_votes",
            description="Get recent votes from House or Senate",
            inputSchema={
                "type": "object",
                "properties": {
                    "chamber": {"type": "string", "enum": ["house", "senate"], "description": "Chamber"},
                    "limit": {"type": "integer", "description": "Number of votes to retrieve (default 10)"}
                },
                "required": ["chamber"]
            }
        ),
        types.Tool(
            name="get_committee",
            description="Get information about a congressional committee",
            inputSchema={
                "type": "object",
                "properties": {
                    "chamber": {"type": "string", "enum": ["house", "senate"], "description": "Chamber"},
                    "committee_code": {"type": "string", "description": "Committee code"}
                },
                "required": ["chamber", "committee_code"]
            }
        ),
        types.Tool(
            name="search_amendments",
            description="Search for amendments to bills",
            inputSchema={
                "type": "object",
                "properties": {
                    "congress": {"type": "integer", "description": "Congress number"},
                    "limit": {"type": "integer", "description": "Maximum results (default 20)"}
                }
            }
        ),
        types.Tool(
            name="search_govinfo",
            description="Search GovInfo for official government documents",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "collection": {"type": "string", "description": "Collection to search (e.g., BILLS, PLAW, FR)"},
                    "limit": {"type": "integer", "description": "Maximum results (default 20)"}
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="get_public_law",
            description="Get information about a public law",
            inputSchema={
                "type": "object",
                "properties": {
                    "congress": {"type": "integer", "description": "Congress number"},
                    "law_number": {"type": "integer", "description": "Public law number"}
                },
                "required": ["congress", "law_number"]
            }
        ),
        types.Tool(
            name="get_congressional_record",
            description="Search the Congressional Record for floor proceedings",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "Date (YYYY-MM-DD)"},
                    "chamber": {"type": "string", "enum": ["house", "senate", "extensions"], "description": "Section"}
                },
                "required": ["date"]
            }
        ),
        types.Tool(
            name="get_federal_register",
            description="Search the Federal Register for rules and notices",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "agency": {"type": "string", "description": "Agency name"},
                    "document_type": {"type": "string", "enum": ["rule", "proposed_rule", "notice"], "description": "Document type"},
                    "limit": {"type": "integer", "description": "Maximum results (default 20)"}
                }
            }
        ),
        types.Tool(
            name="calculate_legislative_stats",
            description="Calculate statistics about legislative activity",
            inputSchema={
                "type": "object",
                "properties": {
                    "congress": {"type": "integer", "description": "Congress number"},
                    "chamber": {"type": "string", "enum": ["house", "senate", "both"], "description": "Chamber"}
                },
                "required": ["congress"]
            }
        ),
        types.Tool(
            name="get_congress_overview",
            description="Get educational overview of how Congress works",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="get_legislative_process",
            description="Learn about the legislative process and how bills become laws",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]
    
    # Filter tools based on permissions if authenticated
    if REQUIRE_AUTH and current_token_info:
        permissions = current_token_info.get('permissions', 'read_only')
        if permissions == 'read_only':
            # Filter to only read tools
            read_tools = ['authenticate', 'get_token_info', 'search_bills', 'get_bill', 
                         'get_member', 'get_committee', 'get_congress_overview', 
                         'get_legislative_process', 'search_amendments']
            all_tools = [t for t in all_tools if t.name in read_tools]
    
    return all_tools

@server.call_tool()
async def handle_call_tool(
    name: str, 
    arguments: dict
) -> list[types.TextContent]:
    """Handle tool execution with authentication check."""
    
    # Authentication tools always allowed
    if name == "authenticate":
        token = arguments.get("token", "")
        if not token:
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "error": "Token required",
                    "status": "authentication_failed"
                }, indent=2)
            )]
        
        token_info = token_manager.validate_token(token)
        if not token_info:
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "error": "Invalid or expired token",
                    "status": "authentication_failed"
                }, indent=2)
            )]
        
        # Set current session info
        global current_token_info
        current_token_info = token_info
        
        # Record authentication
        token_manager.record_usage(token_info['id'], 'authenticate')
        
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "status": "authenticated",
                "token_id": token_info['id'],
                "name": token_info['name'],
                "permissions": token_info['permissions'],
                "usage_count": token_info['usage_count'],
                "message": f"Successfully authenticated as '{token_info['name']}' with {token_info['permissions']} permissions"
            }, indent=2)
        )]
    
    if name == "get_token_info":
        if not current_token_info:
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "error": "Not authenticated",
                    "message": "Use the 'authenticate' tool first with your API token"
                }, indent=2)
            )]
        
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "token_id": current_token_info['id'],
                "name": current_token_info['name'],
                "permissions": current_token_info['permissions'],
                "created_at": current_token_info['created_at'],
                "last_used": current_token_info['last_used'],
                "usage_count": current_token_info['usage_count'],
                "expires_at": current_token_info.get('expires_at', 'Never')
            }, indent=2)
        )]
    
    # Check authentication for other tools
    if REQUIRE_AUTH and not current_token_info:
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "error": "Authentication required",
                "message": "Use the 'authenticate' tool first with your API token"
            }, indent=2)
        )]
    
    # Check permissions
    if not await check_permission(name):
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "error": "Permission denied",
                "message": f"Your token ({current_token_info['permissions']}) doesn't have permission to use '{name}'"
            }, indent=2)
        )]
    
    # Record tool usage
    if current_token_info:
        token_manager.record_usage(current_token_info['id'], name)
    
    # Check cache
    cache_key = get_cache_key(name, arguments)
    if cache_key in cache:
        cached_data, cached_time = cache[cache_key]
        if datetime.utcnow() - cached_time < CACHE_TTL:
            return [types.TextContent(
                type="text",
                text=json.dumps(cached_data, indent=2)
            )]
    
    try:
        # Execute the actual tool logic
        if name == "search_bills":
            query = arguments.get("query", "")
            congress = arguments.get("congress", 118)
            chamber = arguments.get("chamber", "both")
            limit = arguments.get("limit", 20)
            
            url = f"https://api.congress.gov/v3/bill/{congress}"
            params = {"format": "json", "limit": limit}
            if query:
                params["fromDateTime"] = "2023-01-01T00:00:00Z"
            
            headers = {"X-Api-Key": CONGRESS_API_KEY} if CONGRESS_API_KEY else {}
            response = await client.get(url, params=params, headers=headers)
            data = response.json()
            
            bills = data.get("bills", [])
            if query:
                bills = [b for b in bills if query.lower() in b.get("title", "").lower()]
            
            result = {
                "results": bills[:limit],
                "count": len(bills),
                "source": format_source("congress", f"Congress {congress} Bills")
            }
            
        elif name == "get_bill":
            congress = arguments["congress"]
            bill_type = arguments["bill_type"]
            bill_number = arguments["bill_number"]
            
            url = f"https://api.congress.gov/v3/bill/{congress}/{bill_type}/{bill_number}"
            headers = {"X-Api-Key": CONGRESS_API_KEY} if CONGRESS_API_KEY else {}
            response = await client.get(url, params={"format": "json"}, headers=headers)
            data = response.json()
            
            result = {
                "bill": data.get("bill", {}),
                "source": format_source("congress", f"{bill_type.upper()} {bill_number} ({congress}th Congress)")
            }
            
        elif name == "get_member":
            bioguide_id = arguments["bioguide_id"]
            
            url = f"https://api.congress.gov/v3/member/{bioguide_id}"
            headers = {"X-Api-Key": CONGRESS_API_KEY} if CONGRESS_API_KEY else {}
            response = await client.get(url, params={"format": "json"}, headers=headers)
            data = response.json()
            
            result = {
                "member": data.get("member", {}),
                "source": format_source("congress", f"Member {bioguide_id}")
            }
            
        elif name == "get_congress_overview":
            result = {
                "overview": {
                    "title": "United States Congress Overview",
                    "description": "The legislative branch of the U.S. federal government",
                    "structure": {
                        "senate": {
                            "members": 100,
                            "term": "6 years",
                            "per_state": 2,
                            "minimum_age": 30,
                            "presiding_officer": "Vice President"
                        },
                        "house": {
                            "members": 435,
                            "term": "2 years",
                            "distribution": "Based on population",
                            "minimum_age": 25,
                            "presiding_officer": "Speaker of the House"
                        }
                    },
                    "powers": [
                        "Make laws",
                        "Declare war",
                        "Approve treaties (Senate)",
                        "Confirm appointments (Senate)",
                        "Impeachment (House initiates, Senate tries)",
                        "Override presidential vetoes",
                        "Control federal budget"
                    ],
                    "current_congress": 118,
                    "session_period": "2023-2024"
                },
                "source": format_source("calculation", "Congressional Structure Analysis")
            }
            
        elif name == "get_legislative_process":
            result = {
                "process": {
                    "title": "How a Bill Becomes a Law",
                    "steps": [
                        {
                            "step": 1,
                            "name": "Introduction",
                            "description": "A member of Congress introduces a bill"
                        },
                        {
                            "step": 2,
                            "name": "Committee Review",
                            "description": "Bill is referred to committee for study and hearings"
                        },
                        {
                            "step": 3,
                            "name": "Committee Action",
                            "description": "Committee may amend, approve, or table the bill"
                        },
                        {
                            "step": 4,
                            "name": "Floor Action",
                            "description": "Full chamber debates and votes on the bill"
                        },
                        {
                            "step": 5,
                            "name": "Other Chamber",
                            "description": "Bill goes to other chamber, repeats process"
                        },
                        {
                            "step": 6,
                            "name": "Conference Committee",
                            "description": "Resolves differences between House and Senate versions"
                        },
                        {
                            "step": 7,
                            "name": "Final Approval",
                            "description": "Both chambers vote on identical version"
                        },
                        {
                            "step": 8,
                            "name": "Presidential Action",
                            "description": "President signs, vetoes, or allows to become law"
                        }
                    ],
                    "key_terms": {
                        "filibuster": "Senate procedure to delay or block a vote",
                        "cloture": "Procedure to end a filibuster (requires 60 votes)",
                        "markup": "Committee process of amending a bill",
                        "quorum": "Minimum members required to conduct business",
                        "rider": "Amendment unrelated to bill's main purpose"
                    }
                },
                "source": format_source("calculation", "Legislative Process Education")
            }
            
        else:
            result = {
                "error": f"Tool '{name}' implementation not complete",
                "message": "This tool is still being implemented"
            }
        
        # Cache the result
        cache[cache_key] = (result, datetime.utcnow())
        
        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
        
    except Exception as e:
        error_result = {
            "error": str(e),
            "tool": name,
            "message": "An error occurred while processing your request"
        }
        return [types.TextContent(
            type="text",
            text=json.dumps(error_result, indent=2)
        )]

async def main():
    """Run the server with stdio transport."""
    
    # Show authentication status
    if REQUIRE_AUTH:
        print(f"🔐 Authentication: ENABLED", file=sys.stderr)
        print(f"   Create tokens with: python token_manager.py create 'Token Name'", file=sys.stderr)
    else:
        print(f"⚠️  Authentication: DISABLED (set REQUIRE_AUTH=true to enable)", file=sys.stderr)
    
    print(f"📊 EnactAI Data MCP Server (Local with Auth)", file=sys.stderr)
    print(f"   Congress.gov API: {'✓' if CONGRESS_API_KEY else '✗ (limited)'}", file=sys.stderr)
    print(f"   GovInfo API: {'✓' if GOVINFO_API_KEY else '✗ (limited)'}", file=sys.stderr)
    
    async with stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="enactai-data-local-auth",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())