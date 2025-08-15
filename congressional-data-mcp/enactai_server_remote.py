#!/usr/bin/env python3
"""
EnactAI Data Remote MCP Server
Provides legislative data access via SSE transport for remote connections
"""

import os
import json
import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from collections import defaultdict
import hashlib

# FastAPI for SSE transport
from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# MCP imports
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.sse as sse
import mcp.types as types

# Configuration
CONGRESS_API_KEY = os.getenv("CONGRESS_GOV_API_KEY", "")
GOVINFO_API_KEY = os.getenv("GOVINFO_API_KEY", "")
API_TOKEN = os.getenv("ENACTAI_API_TOKEN", "")  # For simple auth
PORT = int(os.getenv("PORT", "8082"))

# Create FastAPI app
app = FastAPI(title="EnactAI Data MCP Server", version="2.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create MCP server
mcp_server = Server("enactai-data")

# HTTP client for external APIs
client = httpx.AsyncClient(timeout=30.0)

# Cache for API responses (TTL: 5 minutes)
cache: Dict[str, tuple[Any, datetime]] = {}
CACHE_TTL = timedelta(minutes=5)

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

# Authentication dependency
async def verify_token(authorization: Optional[str] = Header(None)):
    """Simple token verification for API access."""
    if API_TOKEN and API_TOKEN != "":
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
        token = authorization.replace("Bearer ", "")
        if token != API_TOKEN:
            raise HTTPException(status_code=401, detail="Invalid API token")
    return True

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "enactai-data", "version": "2.0.0"}

@mcp_server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List all available tools."""
    return [
        types.Tool(
            name="get_bill",
            description="Get comprehensive information about a specific bill including sponsors, actions, and current status",
            inputSchema={
                "type": "object",
                "properties": {
                    "congress": {"type": "integer", "description": "Congress number (e.g., 118 for 2023-2024)"},
                    "bill_type": {"type": "string", "description": "Bill type (hr, s, hjres, sjres)"},
                    "bill_number": {"type": "integer", "description": "Bill number"}
                },
                "required": ["congress", "bill_type", "bill_number"]
            }
        ),
        types.Tool(
            name="search_bills",
            description="Search for bills in Congress with various filters",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query text"},
                    "congress": {"type": "integer", "description": "Congress number (default: current)"},
                    "chamber": {"type": "string", "description": "Chamber (house, senate, both)", "default": "both"},
                    "limit": {"type": "integer", "description": "Number of results", "default": 20}
                }
            }
        ),
        types.Tool(
            name="track_bill_progress",
            description="Track the detailed progress of a bill through the legislative process",
            inputSchema={
                "type": "object",
                "properties": {
                    "congress": {"type": "integer", "description": "Congress number"},
                    "bill_type": {"type": "string", "description": "Bill type"},
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
                    "bioguide_id": {"type": "string", "description": "Bioguide ID (e.g., 'P000197')"}
                },
                "required": ["bioguide_id"]
            }
        ),
        types.Tool(
            name="search_members",
            description="Search for members of Congress by name, state, or party",
            inputSchema={
                "type": "object",
                "properties": {
                    "state": {"type": "string", "description": "Two-letter state code"},
                    "party": {"type": "string", "description": "Party (D, R, I)"},
                    "chamber": {"type": "string", "description": "Chamber (house, senate)"},
                    "current_only": {"type": "boolean", "description": "Only current members", "default": True}
                }
            }
        ),
        types.Tool(
            name="get_committee",
            description="Get information about a congressional committee",
            inputSchema={
                "type": "object",
                "properties": {
                    "chamber": {"type": "string", "description": "Chamber (house, senate)"},
                    "committee_code": {"type": "string", "description": "Committee code (e.g., 'HSJU')"}
                },
                "required": ["chamber", "committee_code"]
            }
        ),
        types.Tool(
            name="get_vote",
            description="Get details about a specific vote in Congress",
            inputSchema={
                "type": "object",
                "properties": {
                    "congress": {"type": "integer", "description": "Congress number"},
                    "chamber": {"type": "string", "description": "Chamber (house, senate)"},
                    "session": {"type": "integer", "description": "Session number"},
                    "roll_call": {"type": "integer", "description": "Roll call number"}
                },
                "required": ["congress", "chamber", "session", "roll_call"]
            }
        ),
        types.Tool(
            name="search_govinfo",
            description="Search Government Publishing Office documents including laws, regulations, and reports",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "collection": {"type": "string", "description": "Collection (BILLS, PLAW, FR, CFR, CRPT)"},
                    "date_from": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                    "date_to": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                    "limit": {"type": "integer", "description": "Number of results", "default": 20}
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
            description="Search the Congressional Record for debates and proceedings",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "Date (YYYY-MM-DD)"},
                    "section": {"type": "string", "description": "Section (house, senate, extensions)"},
                    "keywords": {"type": "string", "description": "Keywords to search"}
                },
                "required": ["date"]
            }
        ),
        types.Tool(
            name="get_member_votes",
            description="Get voting history for a member of Congress",
            inputSchema={
                "type": "object",
                "properties": {
                    "bioguide_id": {"type": "string", "description": "Member's bioguide ID"},
                    "congress": {"type": "integer", "description": "Congress number"},
                    "limit": {"type": "integer", "description": "Number of votes to return", "default": 50}
                },
                "required": ["bioguide_id"]
            }
        ),
        types.Tool(
            name="get_congress_calendar",
            description="Get the congressional calendar and schedule",
            inputSchema={
                "type": "object",
                "properties": {
                    "chamber": {"type": "string", "description": "Chamber (house, senate, both)", "default": "both"},
                    "date_from": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                    "date_to": {"type": "string", "description": "End date (YYYY-MM-DD)"}
                }
            }
        ),
        types.Tool(
            name="get_legislative_process",
            description="Educational tool: Learn about how bills become laws and the legislative process",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Topic (overview, committees, voting, reconciliation, filibuster)"}
                }
            }
        ),
        types.Tool(
            name="get_congress_overview",
            description="Get overview information about a specific Congress including leadership and statistics",
            inputSchema={
                "type": "object",
                "properties": {
                    "congress": {"type": "integer", "description": "Congress number (default: current 118)"}
                }
            }
        )
    ]

@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Handle tool execution with caching and source citations."""
    
    # Check cache first
    cache_key = get_cache_key(name, arguments)
    if cache_key in cache:
        cached_data, cached_time = cache[cache_key]
        if datetime.now() - cached_time < CACHE_TTL:
            return cached_data
    
    result = await execute_tool(name, arguments)
    
    # Cache the result
    cache[cache_key] = (result, datetime.now())
    
    return result

async def execute_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Execute the specific tool."""
    
    if name == "get_bill":
        try:
            congress = arguments["congress"]
            bill_type = arguments["bill_type"]
            bill_number = arguments["bill_number"]
            
            url = f"https://api.congress.gov/v3/bill/{congress}/{bill_type}/{bill_number}"
            headers = {"X-Api-Key": CONGRESS_API_KEY}
            params = {"format": "json"}
            
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            bill_info = data.get("bill", {})
            
            # Get additional details
            actions_url = f"{url}/actions"
            cosponsors_url = f"{url}/cosponsors"
            
            actions_resp = await client.get(actions_url, headers=headers, params=params)
            cosponsors_resp = await client.get(cosponsors_url, headers=headers, params=params)
            
            actions_data = actions_resp.json() if actions_resp.status_code == 200 else {}
            cosponsors_data = cosponsors_resp.json() if cosponsors_resp.status_code == 200 else {}
            
            result = {
                "bill_id": f"{bill_type}{bill_number}-{congress}",
                "congress": bill_info.get("congress"),
                "type": bill_info.get("type"),
                "number": bill_info.get("number"),
                "title": bill_info.get("title"),
                "short_title": bill_info.get("titles", [{}])[0].get("title") if bill_info.get("titles") else None,
                "sponsor": {
                    "name": bill_info.get("sponsors", [{}])[0].get("fullName") if bill_info.get("sponsors") else None,
                    "party": bill_info.get("sponsors", [{}])[0].get("party") if bill_info.get("sponsors") else None,
                    "state": bill_info.get("sponsors", [{}])[0].get("state") if bill_info.get("sponsors") else None
                },
                "cosponsors_count": cosponsors_data.get("pagination", {}).get("count", 0),
                "introduced_date": bill_info.get("introducedDate"),
                "latest_action": {
                    "date": bill_info.get("latestAction", {}).get("actionDate"),
                    "text": bill_info.get("latestAction", {}).get("text")
                },
                "policy_area": bill_info.get("policyArea", {}).get("name") if bill_info.get("policyArea") else None,
                "committees": [c.get("name") for c in bill_info.get("committees", {}).get("item", [])],
                "legislative_subjects": [s.get("name") for s in bill_info.get("subjects", {}).get("legislativeSubjects", {}).get("item", [])][:5],
                "status": "Became Law" if bill_info.get("laws") else "Active",
                "actions_count": actions_data.get("pagination", {}).get("count", 0),
                "url": bill_info.get("url"),
                "source": format_source("congress", f"{bill_type}{bill_number}-{congress}")
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
            query = arguments.get("query", "")
            congress = arguments.get("congress", 118)
            limit = arguments.get("limit", 20)
            
            url = f"https://api.congress.gov/v3/bill/{congress}"
            headers = {"X-Api-Key": CONGRESS_API_KEY}
            params = {
                "format": "json",
                "limit": limit,
                "sort": "updateDate+desc"
            }
            
            if query:
                params["q"] = query
            
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            bills = data.get("bills", [])
            
            results = []
            for bill in bills[:limit]:
                results.append({
                    "bill_id": f"{bill.get('type')}{bill.get('number')}-{bill.get('congress')}",
                    "title": bill.get("title"),
                    "type": bill.get("type"),
                    "number": bill.get("number"),
                    "congress": bill.get("congress"),
                    "introduced_date": bill.get("introducedDate"),
                    "latest_action": bill.get("latestAction", {}).get("text"),
                    "sponsor": bill.get("sponsors", [{}])[0].get("name") if bill.get("sponsors") else None,
                    "url": bill.get("url")
                })
            
            response_data = {
                "results": results,
                "count": len(results),
                "source": format_source("congress", f"Congress {congress} Bills Search")
            }
            
            return [types.TextContent(
                type="text",
                text=json.dumps(response_data, indent=2)
            )]
            
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Error searching bills: {str(e)}"
            )]
    
    elif name == "track_bill_progress":
        try:
            congress = arguments["congress"]
            bill_type = arguments["bill_type"]
            bill_number = arguments["bill_number"]
            
            # Get bill details and actions
            url = f"https://api.congress.gov/v3/bill/{congress}/{bill_type}/{bill_number}"
            actions_url = f"{url}/actions"
            headers = {"X-Api-Key": CONGRESS_API_KEY}
            params = {"format": "json", "limit": 250}
            
            bill_resp = await client.get(url, headers=headers, params={"format": "json"})
            actions_resp = await client.get(actions_url, headers=headers, params=params)
            
            bill_data = bill_resp.json().get("bill", {})
            actions_data = actions_resp.json()
            
            # Process actions to track progress
            stages = {
                "introduced": {"completed": False, "date": None, "description": "Bill introduced"},
                "committee": {"completed": False, "date": None, "description": "Referred to committee"},
                "committee_action": {"completed": False, "date": None, "description": "Committee action"},
                "house_passage": {"completed": False, "date": None, "description": "Passed House"},
                "senate_passage": {"completed": False, "date": None, "description": "Passed Senate"},
                "resolving_differences": {"completed": False, "date": None, "description": "Resolving differences"},
                "to_president": {"completed": False, "date": None, "description": "Sent to President"},
                "became_law": {"completed": False, "date": None, "description": "Became Law"}
            }
            
            # Analyze actions to determine progress
            for action in actions_data.get("actions", []):
                action_text = action.get("text", "").lower()
                action_date = action.get("actionDate")
                
                if "introduced" in action_text:
                    stages["introduced"]["completed"] = True
                    stages["introduced"]["date"] = action_date
                elif "referred to" in action_text and "committee" in action_text:
                    stages["committee"]["completed"] = True
                    stages["committee"]["date"] = action_date
                elif "reported" in action_text or "ordered to be reported" in action_text:
                    stages["committee_action"]["completed"] = True
                    stages["committee_action"]["date"] = action_date
                elif "passed house" in action_text:
                    stages["house_passage"]["completed"] = True
                    stages["house_passage"]["date"] = action_date
                elif "passed senate" in action_text:
                    stages["senate_passage"]["completed"] = True
                    stages["senate_passage"]["date"] = action_date
                elif "conference" in action_text or "amendment" in action_text:
                    stages["resolving_differences"]["completed"] = True
                    stages["resolving_differences"]["date"] = action_date
                elif "presented to president" in action_text:
                    stages["to_president"]["completed"] = True
                    stages["to_president"]["date"] = action_date
                elif "became law" in action_text or "signed by president" in action_text:
                    stages["became_law"]["completed"] = True
                    stages["became_law"]["date"] = action_date
            
            # Calculate progress percentage
            completed_stages = sum(1 for s in stages.values() if s["completed"])
            progress_percentage = (completed_stages / len(stages)) * 100
            
            result = {
                "bill_id": f"{bill_type}{bill_number}-{congress}",
                "title": bill_data.get("title"),
                "current_status": bill_data.get("latestAction", {}).get("text"),
                "progress_percentage": round(progress_percentage, 1),
                "stages": stages,
                "total_actions": actions_data.get("pagination", {}).get("count", 0),
                "introduced_date": bill_data.get("introducedDate"),
                "last_action_date": bill_data.get("latestAction", {}).get("actionDate"),
                "became_law": stages["became_law"]["completed"],
                "source": format_source("congress", f"Bill Progress Tracking - {bill_type}{bill_number}-{congress}")
            }
            
            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
            
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Error tracking bill progress: {str(e)}"
            )]
    
    elif name == "get_legislative_process":
        topics = {
            "overview": {
                "title": "How a Bill Becomes a Law",
                "steps": [
                    "1. Introduction: A bill is introduced in either the House or Senate",
                    "2. Committee Review: Bill is referred to appropriate committee(s)",
                    "3. Committee Action: Hearings, markup, and vote",
                    "4. Floor Action: Debate and voting in the chamber",
                    "5. Other Chamber: Process repeats in the other chamber",
                    "6. Conference Committee: Reconciles differences between versions",
                    "7. Final Passage: Both chambers pass identical version",
                    "8. Presidential Action: Sign into law, veto, or pocket veto",
                    "9. Override: Congress can override veto with 2/3 majority"
                ],
                "timeline": "Average bill takes 5.5 months; only about 3% become law"
            },
            "committees": {
                "title": "Congressional Committees",
                "types": {
                    "Standing": "Permanent committees with legislative jurisdiction",
                    "Select": "Temporary committees for specific purposes",
                    "Joint": "Committees with members from both chambers",
                    "Conference": "Temporary committees to reconcile bill differences"
                },
                "process": "Committees review bills, hold hearings, make amendments, and vote on whether to report bills to the floor"
            },
            "voting": {
                "title": "Voting in Congress",
                "methods": {
                    "Voice Vote": "Members say 'Aye' or 'No'",
                    "Division Vote": "Members stand to be counted",
                    "Recorded Vote": "Electronic voting or roll call"
                },
                "requirements": {
                    "Simple Majority": "Most legislation (50% + 1)",
                    "Supermajority": "Constitutional amendments (2/3), veto override (2/3), cloture (3/5 in Senate)"
                }
            },
            "filibuster": {
                "title": "The Senate Filibuster",
                "description": "A procedural tactic to delay or prevent a vote",
                "cloture": "Requires 60 votes to end debate and proceed to a vote",
                "exceptions": "Budget reconciliation, judicial nominations (simple majority)"
            }
        }
        
        topic = arguments.get("topic", "overview")
        content = topics.get(topic, topics["overview"])
        
        result = {
            "topic": topic,
            "content": content,
            "source": format_source("calculation", "EnactAI Legislative Education")
        }
        
        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
    
    elif name == "get_congress_overview":
        try:
            congress = arguments.get("congress", 118)
            
            # Provide overview based on congress number
            congress_info = {
                118: {
                    "years": "2023-2024",
                    "president": "Joe Biden",
                    "senate_majority": "Democrats (51-49)",
                    "house_majority": "Republicans (222-213)",
                    "senate_leader": "Chuck Schumer (D-NY)",
                    "house_speaker": "Mike Johnson (R-LA)",
                    "notable_legislation": [
                        "Infrastructure Investment and Jobs Act continuation",
                        "CHIPS and Science Act implementation",
                        "Debt ceiling negotiations"
                    ]
                },
                117: {
                    "years": "2021-2022",
                    "president": "Joe Biden",
                    "senate_majority": "Democrats (50-50 + VP)",
                    "house_majority": "Democrats (222-213)",
                    "senate_leader": "Chuck Schumer (D-NY)",
                    "house_speaker": "Nancy Pelosi (D-CA)",
                    "notable_legislation": [
                        "American Rescue Plan Act",
                        "Infrastructure Investment and Jobs Act",
                        "Inflation Reduction Act"
                    ]
                }
            }
            
            info = congress_info.get(congress, {
                "years": f"{2023 + (congress - 118) * 2}-{2024 + (congress - 118) * 2}",
                "note": "Historical data available through Congress.gov API"
            })
            
            result = {
                "congress_number": congress,
                "details": info,
                "source": format_source("calculation", f"Congress {congress} Overview")
            }
            
            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
            
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Error getting congress overview: {str(e)}"
            )]
    
    # Add handlers for other tools following similar patterns...
    
    else:
        return [types.TextContent(
            type="text",
            text=f"Tool '{name}' is not yet implemented in remote mode"
        )]

# SSE endpoint for MCP
@app.get("/sse")
async def handle_sse(request: Request, _: bool = Depends(verify_token)):
    """Handle SSE connection for MCP protocol."""
    from sse_starlette.sse import EventSourceResponse
    import json
    
    async def event_generator():
        # Simple SSE event to test connectivity
        yield {
            "event": "connected",
            "data": json.dumps({
                "server": "enactai-data",
                "version": "2.0.0",
                "status": "ready"
            })
        }
        
        # Keep connection alive
        while True:
            await asyncio.sleep(30)  # Ping every 30 seconds
            yield {
                "event": "ping",
                "data": json.dumps({"timestamp": datetime.now().isoformat()})
            }
    
    return EventSourceResponse(event_generator())

# OpenAPI schema endpoint
@app.get("/openapi.json")
async def get_openapi():
    """Get OpenAPI schema for the API."""
    return app.openapi()

if __name__ == "__main__":
    # Run with uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)