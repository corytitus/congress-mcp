#!/usr/bin/env python3
"""
EnactAI Data MCP Server with Stateless Authentication
Each tool call includes the token for validation
"""

import os
import json
import asyncio
import httpx
from datetime import datetime, timedelta, timezone
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
server = Server("enactai-data-stateless")
token_manager = TokenManager()

# HTTP client for external APIs
client = httpx.AsyncClient(timeout=30.0)

# Cache for API responses (TTL: 5 minutes)
cache: Dict[str, tuple[Any, datetime]] = {}
CACHE_TTL = timedelta(minutes=5)

# Cache for current Congress (TTL: 1 day)
current_congress_cache: Optional[tuple[int, datetime]] = None
CONGRESS_CACHE_TTL = timedelta(days=1)

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

async def get_current_congress() -> int:
    """Get the current Congress number from the API"""
    global current_congress_cache
    
    # Check cache first
    if current_congress_cache:
        congress_num, cached_time = current_congress_cache
        if datetime.now(timezone.utc) - cached_time < CONGRESS_CACHE_TTL:
            return congress_num
    
    try:
        # Get current Congress from API
        headers = {"X-Api-Key": CONGRESS_API_KEY} if CONGRESS_API_KEY else {}
        response = await client.get(
            "https://api.congress.gov/v3/congress/current",
            params={"format": "json"},
            headers=headers
        )
        data = response.json()
        
        # Extract Congress number
        if "congress" in data:
            congress_info = data["congress"]
            congress_num = congress_info.get("number", 119)
        else:
            # Fallback to 119 if API doesn't return expected format
            congress_num = 119
        
        # Cache the result
        current_congress_cache = (congress_num, datetime.now(timezone.utc))
        return congress_num
        
    except Exception as e:
        print(f"Error getting current Congress: {e}", file=sys.stderr)
        # Default to 119th Congress as fallback
        return 119

def validate_token_inline(token: str) -> Optional[Dict]:
    """Validate token inline for stateless operation"""
    if not REQUIRE_AUTH:
        return {"permissions": "admin", "name": "No Auth Required", "id": "noauth"}
    
    if not token:
        return None
    
    return token_manager.validate_token(token)

def check_permission(token_info: Dict, tool_name: str) -> bool:
    """Check if token has permission to use tool"""
    if not REQUIRE_AUTH:
        return True
    
    if not token_info:
        return False
    
    permissions = token_info.get('permissions', 'read_only')
    
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
    """List all available tools."""
    # Common token parameter for all tools
    token_param = {
        "token": {
            "type": "string", 
            "description": "Your API token (required if authentication is enabled)"
        }
    }
    
    tools = [
        types.Tool(
            name="authenticate",
            description="Authenticate and validate your API token",
            inputSchema={
                "type": "object",
                "properties": {
                    "token": {"type": "string", "description": "Your API token"}
                },
                "required": ["token"]
            }
        ),
        types.Tool(
            name="search_bills",
            description="Search for congressional bills with advanced filtering",
            inputSchema={
                "type": "object",
                "properties": {
                    **token_param,
                    "query": {"type": "string", "description": "Search query"},
                    "congress": {"type": "integer", "description": "Congress number (defaults to current Congress from API, e.g., 119 for 2025-2026)"},
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
                    **token_param,
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
                    **token_param,
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
                    **token_param,
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
                    **token_param,
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
                    **token_param,
                    "congress": {"type": "integer", "description": "Congress number"},
                    "limit": {"type": "integer", "description": "Maximum results (default 20)"}
                }
            }
        ),
        types.Tool(
            name="get_current_congress",
            description="Get information about the current Congress session",
            inputSchema={
                "type": "object",
                "properties": token_param
            }
        ),
        types.Tool(
            name="get_congress_overview",
            description="Get educational overview of how Congress works",
            inputSchema={
                "type": "object",
                "properties": token_param
            }
        ),
        types.Tool(
            name="get_legislative_process",
            description="Learn about the legislative process and how bills become laws",
            inputSchema={
                "type": "object",
                "properties": token_param
            }
        )
    ]
    
    return tools

@server.call_tool()
async def handle_call_tool(
    name: str, 
    arguments: dict
) -> list[types.TextContent]:
    """Handle tool execution with inline token validation."""
    
    # Extract token from arguments (all tools now include it)
    token = arguments.get("token", "")
    
    # Special handling for authenticate tool
    if name == "authenticate":
        token_info = validate_token_inline(token)
        if not token_info:
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "error": "Invalid or expired token",
                    "status": "authentication_failed"
                }, indent=2)
            )]
        
        # Record authentication
        if token_info.get('id') != 'noauth':
            token_manager.record_usage(token_info['id'], 'authenticate')
        
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "status": "authenticated",
                "token_id": token_info['id'],
                "name": token_info['name'],
                "permissions": token_info['permissions'],
                "message": f"Token validated! Include this token in all subsequent tool calls.",
                "important": "Remember to pass your token with every tool call"
            }, indent=2)
        )]
    
    # For all other tools, validate token
    if REQUIRE_AUTH:
        token_info = validate_token_inline(token)
        if not token_info:
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "error": "Authentication required",
                    "message": "Please provide your API token",
                    "hint": "Include 'token' parameter with your API token"
                }, indent=2)
            )]
        
        # Check permissions
        if not check_permission(token_info, name):
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "error": "Permission denied",
                    "message": f"Your token ({token_info['permissions']}) doesn't have permission to use '{name}'"
                }, indent=2)
            )]
        
        # Record usage
        if token_info.get('id') != 'noauth':
            token_manager.record_usage(token_info['id'], name)
    
    # Remove token from arguments before processing
    args_without_token = {k: v for k, v in arguments.items() if k != 'token'}
    
    # Check cache
    cache_key = get_cache_key(name, args_without_token)
    if cache_key in cache:
        cached_data, cached_time = cache[cache_key]
        if datetime.now(timezone.utc) - cached_time < CACHE_TTL:
            return [types.TextContent(
                type="text",
                text=json.dumps(cached_data, indent=2)
            )]
    
    try:
        # Execute the actual tool logic
        if name == "search_bills":
            query = args_without_token.get("query", "")
            # Get current Congress dynamically if not specified
            if "congress" not in args_without_token:
                congress = await get_current_congress()
            else:
                congress = args_without_token["congress"]
            chamber = args_without_token.get("chamber", "both")
            limit = args_without_token.get("limit", 20)
            
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
            congress = args_without_token["congress"]
            bill_type = args_without_token["bill_type"]
            bill_number = args_without_token["bill_number"]
            
            url = f"https://api.congress.gov/v3/bill/{congress}/{bill_type}/{bill_number}"
            headers = {"X-Api-Key": CONGRESS_API_KEY} if CONGRESS_API_KEY else {}
            response = await client.get(url, params={"format": "json"}, headers=headers)
            data = response.json()
            
            result = {
                "bill": data.get("bill", {}),
                "source": format_source("congress", f"{bill_type.upper()} {bill_number} ({congress}th Congress)")
            }
            
        elif name == "get_member":
            bioguide_id = args_without_token["bioguide_id"]
            
            url = f"https://api.congress.gov/v3/member/{bioguide_id}"
            headers = {"X-Api-Key": CONGRESS_API_KEY} if CONGRESS_API_KEY else {}
            response = await client.get(url, params={"format": "json"}, headers=headers)
            data = response.json()
            
            result = {
                "member": data.get("member", {}),
                "source": format_source("congress", f"Member {bioguide_id}")
            }
            
        elif name == "get_current_congress":
            # Get current Congress information from API
            current_num = await get_current_congress()
            
            # Get detailed info about current Congress
            url = f"https://api.congress.gov/v3/congress/{current_num}"
            headers = {"X-Api-Key": CONGRESS_API_KEY} if CONGRESS_API_KEY else {}
            
            try:
                response = await client.get(url, params={"format": "json"}, headers=headers)
                data = response.json()
                congress_data = data.get("congress", {})
                
                result = {
                    "current_congress": {
                        "number": current_num,
                        "name": congress_data.get("name", f"{current_num}th Congress"),
                        "start_year": congress_data.get("startYear", 2025 if current_num == 119 else None),
                        "end_year": congress_data.get("endYear", 2026 if current_num == 119 else None),
                        "sessions": congress_data.get("sessions", []),
                        "type": congress_data.get("type", "CONGRESS")
                    },
                    "note": "Congress sessions run for 2 years, with new Congress every odd year",
                    "source": format_source("congress", f"Congress {current_num} Information")
                }
            except:
                # Fallback if detailed info fails
                result = {
                    "current_congress": {
                        "number": current_num,
                        "name": f"{current_num}th Congress",
                        "start_year": 2025 if current_num == 119 else 2023,
                        "end_year": 2026 if current_num == 119 else 2024,
                        "note": "Current session"
                    },
                    "source": format_source("congress", f"Congress {current_num}")
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
                    "current_congress": 119,
                    "session_period": "2025-2026",
                    "previous_congress": 118,
                    "previous_period": "2023-2024"
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
        cache[cache_key] = (result, datetime.now(timezone.utc))
        
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
        print(f"🔐 Authentication: ENABLED (Stateless)", file=sys.stderr)
        print(f"   Tokens validated on every request", file=sys.stderr)
    else:
        print(f"⚠️  Authentication: DISABLED (set REQUIRE_AUTH=true to enable)", file=sys.stderr)
    
    print(f"📊 EnactAI Data MCP Server (Stateless Auth)", file=sys.stderr)
    print(f"   Congress.gov API: {'✓' if CONGRESS_API_KEY else '✗ (limited)'}", file=sys.stderr)
    print(f"   GovInfo API: {'✓' if GOVINFO_API_KEY else '✗ (limited)'}", file=sys.stderr)
    
    async with stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="enactai-data-stateless",
                server_version="2.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())