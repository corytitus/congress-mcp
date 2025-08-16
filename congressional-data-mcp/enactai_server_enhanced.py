#!/usr/bin/env python3
"""
EnactAI Data MCP Server - Enhanced Edition
Authoritative legislative data source with comprehensive features
"""

import os
import json
import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import httpx
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types
from document_store import DocumentStore

# Get API keys from environment
CONGRESS_API_KEY = os.getenv("CONGRESS_GOV_API_KEY", "")
GOVINFO_API_KEY = os.getenv("GOVINFO_API_KEY", "")

# Create server
server = Server("enactai-data")

# HTTP client with retries
client = httpx.AsyncClient(
    timeout=30.0,
    limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
    follow_redirects=True
)

# Document storage
doc_store = DocumentStore()

# Simple in-memory cache
cache = {}
CACHE_TTL = 3600  # 1 hour

def get_cache_key(tool: str, args: Dict) -> str:
    """Generate cache key"""
    return f"{tool}:{hashlib.md5(json.dumps(args, sort_keys=True).encode()).hexdigest()}"

def get_from_cache(key: str) -> Optional[Any]:
    """Get from cache if not expired"""
    if key in cache:
        data, timestamp = cache[key]
        if datetime.now().timestamp() - timestamp < CACHE_TTL:
            return data
        else:
            del cache[key]
    return None

def set_cache(key: str, data: Any):
    """Set cache with timestamp"""
    cache[key] = (data, datetime.now().timestamp())

def format_source(api: str, endpoint: str, date_accessed: str = None) -> Dict:
    """Format source citation"""
    if date_accessed is None:
        date_accessed = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    sources = {
        "congress": {
            "name": "U.S. Congress API",
            "authority": "Library of Congress",
            "url": f"https://api.congress.gov{endpoint}",
            "citation": f"U.S. Congress API, Library of Congress, {date_accessed}"
        },
        "govinfo": {
            "name": "GovInfo API",
            "authority": "U.S. Government Publishing Office",
            "url": f"https://api.govinfo.gov{endpoint}",
            "citation": f"GovInfo API, U.S. Government Publishing Office, {date_accessed}"
        }
    }
    
    return sources.get(api, {
        "name": "Unknown Source",
        "authority": "Unknown",
        "url": endpoint,
        "citation": f"Retrieved {date_accessed}"
    })

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools with comprehensive descriptions."""
    return [
        # Bill Tools
        types.Tool(
            name="get_bill",
            description="Get authoritative information about a specific congressional bill including sponsors, actions, and full text",
            inputSchema={
                "type": "object",
                "properties": {
                    "congress": {"type": "integer", "description": "Congress number (e.g., 118 for 2023-2024)"},
                    "bill_type": {"type": "string", "description": "Bill type (hr, s, hjres, sjres, hconres, sconres, hres, sres)"},
                    "bill_number": {"type": "integer", "description": "Bill number"},
                    "include_text": {"type": "boolean", "description": "Include full bill text", "default": False},
                    "include_actions": {"type": "boolean", "description": "Include all actions", "default": True},
                    "include_cosponsors": {"type": "boolean", "description": "Include cosponsor list", "default": False}
                },
                "required": ["congress", "bill_type", "bill_number"]
            }
        ),
        types.Tool(
            name="search_bills",
            description="Search congressional bills with advanced filtering by date, status, committee, and sponsor",
            inputSchema={
                "type": "object",
                "properties": {
                    "congress": {"type": "integer", "description": "Congress number (e.g., 118)", "default": 118},
                    "keyword": {"type": "string", "description": "Search keyword in bill title or text"},
                    "sponsor_state": {"type": "string", "description": "Sponsor's state (2-letter code)"},
                    "status": {"type": "string", "description": "Bill status (introduced, passed_house, passed_senate, enacted)"},
                    "from_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                    "to_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                    "limit": {"type": "integer", "description": "Number of results", "default": 20}
                }
            }
        ),
        
        # Member Tools
        types.Tool(
            name="get_member",
            description="Get comprehensive information about a member of Congress including biography, committees, and voting record",
            inputSchema={
                "type": "object",
                "properties": {
                    "bioguide_id": {"type": "string", "description": "Bioguide ID (e.g., 'P000197')"},
                    "include_votes": {"type": "boolean", "description": "Include recent votes", "default": False},
                    "include_bills": {"type": "boolean", "description": "Include sponsored bills", "default": False}
                },
                "required": ["bioguide_id"]
            }
        ),
        types.Tool(
            name="search_members",
            description="Search for current or historical members of Congress by state, party, or chamber",
            inputSchema={
                "type": "object",
                "properties": {
                    "state": {"type": "string", "description": "State abbreviation (e.g., 'CA')"},
                    "party": {"type": "string", "description": "Party (R, D, I)"},
                    "chamber": {"type": "string", "description": "Chamber (house, senate, both)", "default": "both"},
                    "current_only": {"type": "boolean", "description": "Only current members", "default": True},
                    "limit": {"type": "integer", "default": 50}
                }
            }
        ),
        
        # Vote Tools
        types.Tool(
            name="get_vote",
            description="Get detailed information about a specific congressional vote including individual member votes",
            inputSchema={
                "type": "object",
                "properties": {
                    "congress": {"type": "integer", "description": "Congress number"},
                    "chamber": {"type": "string", "description": "Chamber (house or senate)"},
                    "session": {"type": "integer", "description": "Session (1 or 2)"},
                    "roll_call": {"type": "integer", "description": "Roll call number"}
                },
                "required": ["congress", "chamber", "session", "roll_call"]
            }
        ),
        types.Tool(
            name="get_recent_votes",
            description="Get recent votes from House or Senate with details",
            inputSchema={
                "type": "object",
                "properties": {
                    "chamber": {"type": "string", "description": "Chamber (house, senate, both)", "default": "both"},
                    "days": {"type": "integer", "description": "Number of days to look back", "default": 7},
                    "limit": {"type": "integer", "default": 20}
                }
            }
        ),
        
        # Committee Tools
        types.Tool(
            name="get_committees",
            description="Get information about congressional committees and subcommittees",
            inputSchema={
                "type": "object",
                "properties": {
                    "chamber": {"type": "string", "description": "Chamber (house, senate, joint)", "default": "both"},
                    "committee_code": {"type": "string", "description": "Specific committee code"},
                    "include_members": {"type": "boolean", "description": "Include committee members", "default": True},
                    "include_subcommittees": {"type": "boolean", "description": "Include subcommittees", "default": True}
                }
            }
        ),
        types.Tool(
            name="get_related_bills",
            description="Get bills related to a specific bill (similar bills, procedurally-related bills, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "congress": {"type": "integer", "description": "Congress number (e.g., 118 for 2023-2024)"},
                    "bill_type": {"type": "string", "description": "Bill type (hr, s, hjres, sjres, hres, sres, hconres, sconres)"},
                    "bill_number": {"type": "integer", "description": "Bill number"},
                    "limit": {"type": "integer", "description": "Maximum number of related bills to return", "default": 20}
                },
                "required": ["congress", "bill_type", "bill_number"]
            }
        ),
        
        # GovInfo Tools
        types.Tool(
            name="search_govinfo",
            description="Search authoritative government documents including laws, regulations, and Federal Register",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "collection": {"type": "string", "description": "Collection (BILLS, PLAW, FR, CFR, CREC)"},
                    "congress": {"type": "integer", "description": "Filter by Congress number"},
                    "from_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                    "to_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                    "limit": {"type": "integer", "default": 20}
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="get_public_law",
            description="Get the full text and details of an enacted public law",
            inputSchema={
                "type": "object",
                "properties": {
                    "congress": {"type": "integer", "description": "Congress number"},
                    "law_number": {"type": "integer", "description": "Public law number"},
                    "include_text": {"type": "boolean", "description": "Include full text", "default": True}
                },
                "required": ["congress", "law_number"]
            }
        ),
        
        # Analysis Tools
        types.Tool(
            name="track_legislation",
            description="Track a bill's complete journey from introduction to potential enactment",
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
            name="get_congress_overview",
            description="Get authoritative overview of a specific Congress including leadership, major legislation, and statistics",
            inputSchema={
                "type": "object",
                "properties": {
                    "congress": {"type": "integer", "description": "Congress number (e.g., 118)", "default": 118}
                }
            }
        ),
        
        # Educational/Reference Tools
        types.Tool(
            name="explain_legislative_process",
            description="Get authoritative explanation of the U.S. legislative process and procedures",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string", 
                        "description": "Topic to explain (e.g., 'how a bill becomes law', 'filibuster', 'reconciliation', 'committee process')",
                        "default": "overview"
                    }
                }
            }
        ),
        types.Tool(
            name="get_legislative_calendar",
            description="Get the current legislative calendar and scheduled activities",
            inputSchema={
                "type": "object",
                "properties": {
                    "chamber": {"type": "string", "description": "Chamber (house, senate, both)", "default": "both"},
                    "days_ahead": {"type": "integer", "description": "Number of days to look ahead", "default": 30}
                }
            }
        ),
        
        # Document Storage Tools
        types.Tool(
            name="store_document",
            description="Store a document (text, PDF, or other content) in the document storage system",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Original filename"},
                    "content": {"type": "string", "description": "Document content (text or base64 encoded)"},
                    "title": {"type": "string", "description": "Document title"},
                    "description": {"type": "string", "description": "Document description"},
                    "tags": {"type": "string", "description": "Comma-separated tags"},
                    "category": {"type": "string", "description": "Document category"}
                },
                "required": ["filename", "content"]
            }
        ),
        types.Tool(
            name="search_documents",
            description="Search stored documents by title, content, tags, or other metadata",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "category": {"type": "string", "description": "Filter by category"},
                    "tags": {"type": "string", "description": "Filter by tags (comma-separated)"},
                    "limit": {"type": "integer", "description": "Maximum results to return", "default": 10}
                }
            }
        ),
        types.Tool(
            name="get_document",
            description="Retrieve a specific stored document by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {"type": "string", "description": "Document ID"}
                },
                "required": ["document_id"]
            }
        ),
        types.Tool(
            name="list_documents",
            description="List all stored documents with metadata",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Filter by category"},
                    "limit": {"type": "integer", "description": "Maximum results to return", "default": 20}
                }
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Handle tool execution with caching, error handling, and source citations."""
    
    # Check cache first
    cache_key = get_cache_key(name, arguments)
    cached_result = get_from_cache(cache_key)
    if cached_result:
        return [types.TextContent(type="text", text=cached_result)]
    
    try:
        result = None
        
        # Enhanced get_bill with more details
        if name == "get_bill":
            congress = arguments["congress"]
            bill_type = arguments["bill_type"]
            bill_number = arguments["bill_number"]
            
            # Get basic bill info
            url = f"https://api.congress.gov/v3/bill/{congress}/{bill_type}/{bill_number}"
            headers = {"X-Api-Key": CONGRESS_API_KEY}
            params = {"format": "json"}
            
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            bill_info = data.get("bill", {})
            
            # Build comprehensive result
            result = {
                "bill_id": f"{bill_type}{bill_number}-{congress}",
                "congress": bill_info.get("congress"),
                "type": bill_info.get("type"),
                "number": bill_info.get("number"),
                "title": bill_info.get("title"),
                "short_title": bill_info.get("shortTitle"),
                "sponsor": {
                    "name": bill_info.get("sponsors", [{}])[0].get("fullName") if bill_info.get("sponsors") else None,
                    "bioguide_id": bill_info.get("sponsors", [{}])[0].get("bioguideId") if bill_info.get("sponsors") else None,
                    "state": bill_info.get("sponsors", [{}])[0].get("state") if bill_info.get("sponsors") else None,
                    "party": bill_info.get("sponsors", [{}])[0].get("party") if bill_info.get("sponsors") else None
                },
                "introduced_date": bill_info.get("introducedDate"),
                "policy_area": bill_info.get("policyArea", {}).get("name") if bill_info.get("policyArea") else None,
                "subjects": [s.get("name") for s in bill_info.get("subjects", [])[:5]] if bill_info.get("subjects") else [],
                "summary": bill_info.get("summaries", [{}])[0].get("text") if bill_info.get("summaries") else None,
                "latest_action": {
                    "date": bill_info.get("latestAction", {}).get("actionDate"),
                    "text": bill_info.get("latestAction", {}).get("text")
                },
                "status": determine_bill_status(bill_info),
                "committees": [c.get("name") for c in bill_info.get("committees", [])[:3]] if bill_info.get("committees") else [],
                "cosponsors_count": bill_info.get("cosponsorsCount", 0),
                "urls": {
                    "congress_gov": f"https://www.congress.gov/bill/{congress}th-congress/{format_bill_type(bill_type)}/{bill_number}",
                    "govtrack": f"https://www.govtrack.us/congress/bills/{congress}/{bill_type}{bill_number}",
                    "text": bill_info.get("textVersions", [{}])[0].get("formats", [{}])[0].get("url") if bill_info.get("textVersions") else None
                },
                "source": format_source("congress", url.replace("https://api.congress.gov", ""))
            }
            
            # Get actions if requested
            if arguments.get("include_actions", True):
                actions_url = f"{url}/actions"
                actions_response = await client.get(actions_url, headers=headers, params={"format": "json", "limit": 10})
                if actions_response.status_code == 200:
                    actions_data = actions_response.json()
                    result["actions"] = [
                        {
                            "date": a.get("actionDate"),
                            "text": a.get("text"),
                            "type": a.get("type"),
                            "chamber": a.get("chamber")
                        }
                        for a in actions_data.get("actions", [])[:10]
                    ]
            
            # Get cosponsors if requested
            if arguments.get("include_cosponsors", False):
                cosponsor_url = f"{url}/cosponsors"
                cosponsor_response = await client.get(cosponsor_url, headers=headers, params={"format": "json", "limit": 20})
                if cosponsor_response.status_code == 200:
                    cosponsor_data = cosponsor_response.json()
                    result["cosponsors"] = [
                        {
                            "name": c.get("fullName"),
                            "bioguide_id": c.get("bioguideId"),
                            "party": c.get("party"),
                            "state": c.get("state"),
                            "sponsored_date": c.get("sponsorshipDate")
                        }
                        for c in cosponsor_data.get("cosponsors", [])[:20]
                    ]
        
        # Search bills with advanced filtering
        elif name == "search_bills":
            congress = arguments.get("congress", 118)
            limit = arguments.get("limit", 20)
            
            url = f"https://api.congress.gov/v3/bill/{congress}"
            headers = {"X-Api-Key": CONGRESS_API_KEY}
            params = {"format": "json", "limit": limit, "sort": "updateDate+desc"}
            
            # Add date filtering if provided
            if arguments.get("from_date"):
                params["fromDateTime"] = f"{arguments['from_date']}T00:00:00Z"
            if arguments.get("to_date"):
                params["toDateTime"] = f"{arguments['to_date']}T23:59:59Z"
            
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            bills = data.get("bills", [])
            
            # Format results with source
            result = {
                "search_parameters": {
                    "congress": congress,
                    "keyword": arguments.get("keyword"),
                    "from_date": arguments.get("from_date"),
                    "to_date": arguments.get("to_date"),
                    "results_count": len(bills)
                },
                "bills": [
                    {
                        "bill_id": f"{bill.get('type')}{bill.get('number')}-{congress}",
                        "title": bill.get("title"),
                        "sponsor": bill.get("sponsor", {}).get("fullName"),
                        "sponsor_party": bill.get("sponsor", {}).get("party"),
                        "sponsor_state": bill.get("sponsor", {}).get("state"),
                        "introduced_date": bill.get("introducedDate"),
                        "latest_action": bill.get("latestAction", {}).get("text"),
                        "latest_action_date": bill.get("latestAction", {}).get("actionDate"),
                        "policy_area": bill.get("policyArea", {}).get("name") if bill.get("policyArea") else None,
                        "url": f"https://www.congress.gov/bill/{congress}th-congress/{format_bill_type(bill.get('type'))}/{bill.get('number')}"
                    }
                    for bill in bills
                ],
                "source": format_source("congress", url.replace("https://api.congress.gov", ""))
            }
        
        # Get related bills
        elif name == "get_related_bills":
            congress = arguments["congress"]
            bill_type = arguments["bill_type"]
            bill_number = arguments["bill_number"]
            limit = arguments.get("limit", 20)
            
            url = f"https://api.congress.gov/v3/bill/{congress}/{bill_type}/{bill_number}/relatedbills"
            headers = {"X-Api-Key": CONGRESS_API_KEY}
            params = {"format": "json", "limit": limit}
            
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            related_bills = data.get("relatedBills", [])
            
            # Format the related bills for better readability
            formatted_bills = []
            for bill in related_bills:
                formatted_bill = {
                    "congress": bill.get("congress"),
                    "type": bill.get("type"),
                    "number": bill.get("number"),
                    "title": bill.get("title"),
                    "latestAction": bill.get("latestAction", {}),
                    "relationships": []
                }
                
                # Extract relationship details
                for relationship in bill.get("relationshipDetails", []):
                    formatted_bill["relationships"].append({
                        "type": relationship.get("type"),
                        "identifiedBy": relationship.get("identifiedBy")
                    })
                
                formatted_bills.append(formatted_bill)
            
            result = {
                "originalBill": {
                    "congress": congress,
                    "type": bill_type.upper(),
                    "number": bill_number,
                    "identifier": f"{bill_type.upper()} {bill_number} ({congress}th Congress)"
                },
                "relatedBills": formatted_bills,
                "count": data.get("pagination", {}).get("count", len(related_bills)),
                "source": format_source("congress", f"Related bills for {bill_type.upper()} {bill_number} ({congress}th Congress)")
            }
        
        # Get member with enhanced details
        elif name == "get_member":
            bioguide_id = arguments["bioguide_id"]
            
            url = f"https://api.congress.gov/v3/member/{bioguide_id}"
            headers = {"X-Api-Key": CONGRESS_API_KEY}
            params = {"format": "json"}
            
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            member = data.get("member", {})
            
            # Calculate years of service
            terms = member.get("terms", [])
            first_year = min([int(t.get("startYear", 9999)) for t in terms]) if terms else None
            years_of_service = datetime.now().year - first_year if first_year else 0
            
            result = {
                "bioguide_id": member.get("bioguideId"),
                "name": {
                    "full": member.get("directOrderName"),
                    "first": member.get("firstName"),
                    "last": member.get("lastName"),
                    "suffix": member.get("suffix")
                },
                "current_position": {
                    "chamber": "House" if member.get("district") else "Senate",
                    "state": member.get("state"),
                    "district": member.get("district"),
                    "party": member.get("partyName"),
                    "party_abbreviation": member.get("party")
                },
                "demographics": {
                    "birth_year": member.get("birthYear"),
                    "gender": "Female" if member.get("genderCode") == "F" else "Male" if member.get("genderCode") == "M" else "Other"
                },
                "service": {
                    "years_of_service": years_of_service,
                    "total_terms": len(terms),
                    "first_year": first_year,
                    "current_term_start": terms[-1].get("startYear") if terms else None
                },
                "contact": {
                    "website": member.get("officialWebsiteUrl"),
                    "address": member.get("addressInformation", {}).get("officeAddress"),
                    "phone": member.get("addressInformation", {}).get("phoneNumber")
                },
                "leadership_roles": member.get("leadershipRoles", []),
                "committee_assignments": [
                    {
                        "name": c.get("name"),
                        "rank": c.get("rank"),
                        "side": c.get("side")
                    }
                    for c in member.get("currentCommittees", [])[:10]
                ] if member.get("currentCommittees") else [],
                "urls": {
                    "congress_gov": f"https://www.congress.gov/member/{member.get('firstName')}-{member.get('lastName')}/{bioguide_id}",
                    "official_website": member.get("officialWebsiteUrl")
                },
                "source": format_source("congress", url.replace("https://api.congress.gov", ""))
            }
            
            # Get sponsored bills if requested
            if arguments.get("include_bills", False):
                bills_url = f"{url}/sponsored-legislation"
                bills_response = await client.get(bills_url, headers=headers, params={"format": "json", "limit": 10})
                if bills_response.status_code == 200:
                    bills_data = bills_response.json()
                    result["recent_sponsored_bills"] = [
                        {
                            "title": b.get("title"),
                            "bill_id": f"{b.get('type')}{b.get('number')}-{b.get('congress')}",
                            "introduced_date": b.get("introducedDate"),
                            "latest_action": b.get("latestAction", {}).get("text")
                        }
                        for b in bills_data.get("sponsoredLegislation", [])[:10]
                    ]
        
        # Search members
        elif name == "search_members":
            url = "https://api.congress.gov/v3/member"
            headers = {"X-Api-Key": CONGRESS_API_KEY}
            params = {
                "format": "json",
                "limit": arguments.get("limit", 50),
                "currentMember": arguments.get("current_only", True)
            }
            
            # Add filters
            if arguments.get("state"):
                params["state"] = arguments["state"]
            
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            members = data.get("members", [])
            
            # Filter by party and chamber if specified
            if arguments.get("party"):
                members = [m for m in members if m.get("party") == arguments["party"]]
            
            if arguments.get("chamber") != "both":
                if arguments["chamber"] == "house":
                    members = [m for m in members if m.get("district")]
                elif arguments["chamber"] == "senate":
                    members = [m for m in members if not m.get("district")]
            
            result = {
                "search_parameters": {
                    "state": arguments.get("state"),
                    "party": arguments.get("party"),
                    "chamber": arguments.get("chamber", "both"),
                    "current_only": arguments.get("current_only", True),
                    "results_count": len(members)
                },
                "members": [
                    {
                        "name": m.get("name"),
                        "bioguide_id": m.get("bioguideId"),
                        "state": m.get("state"),
                        "district": m.get("district"),
                        "party": m.get("partyName"),
                        "chamber": "House" if m.get("district") else "Senate",
                        "url": m.get("url")
                    }
                    for m in members
                ],
                "source": format_source("congress", "/v3/member")
            }
        
        # Search GovInfo with enhanced results
        elif name == "search_govinfo":
            query = arguments["query"]
            collection = arguments.get("collection", "")
            limit = arguments.get("limit", 20)
            
            url = "https://api.govinfo.gov/search"
            params = {
                "api_key": GOVINFO_API_KEY,
                "query": query,
                "pageSize": limit
            }
            
            if collection:
                params["collection"] = collection
            if arguments.get("congress"):
                params["congress"] = arguments["congress"]
            if arguments.get("from_date"):
                params["publishedFrom"] = arguments["from_date"]
            if arguments.get("to_date"):
                params["publishedTo"] = arguments["to_date"]
            
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])
            
            result = {
                "search_parameters": {
                    "query": query,
                    "collection": collection or "all",
                    "results_count": len(results),
                    "total_available": data.get("count", 0)
                },
                "documents": [
                    {
                        "title": doc.get("title"),
                        "package_id": doc.get("packageId"),
                        "date_issued": doc.get("dateIssued"),
                        "collection": doc.get("collectionName"),
                        "collection_code": doc.get("collectionCode"),
                        "category": doc.get("category"),
                        "document_type": doc.get("docClass"),
                        "granule_id": doc.get("granuleId"),
                        "urls": {
                            "pdf": doc.get("download", {}).get("pdfLink"),
                            "text": doc.get("download", {}).get("txtLink"),
                            "xml": doc.get("download", {}).get("xmlLink"),
                            "details": doc.get("detailsLink")
                        }
                    }
                    for doc in results
                ],
                "source": format_source("govinfo", "/search")
            }
        
        # Track legislation
        elif name == "track_legislation":
            congress = arguments["congress"]
            bill_type = arguments["bill_type"]
            bill_number = arguments["bill_number"]
            
            # Get bill info from Congress.gov
            bill_url = f"https://api.congress.gov/v3/bill/{congress}/{bill_type}/{bill_number}"
            headers = {"X-Api-Key": CONGRESS_API_KEY}
            
            bill_response = await client.get(bill_url, headers=headers, params={"format": "json"})
            bill_response.raise_for_status()
            bill_data = bill_response.json()
            bill_info = bill_data.get("bill", {})
            
            # Get actions
            actions_url = f"{bill_url}/actions"
            actions_response = await client.get(actions_url, headers=headers, params={"format": "json", "limit": 250})
            actions_data = actions_response.json() if actions_response.status_code == 200 else {"actions": []}
            
            # Determine status
            actions = actions_data.get("actions", [])
            status = analyze_bill_progress(bill_info, actions)
            
            # Check if it became law
            law_info = None
            if "became law" in status["current_stage"].lower() or "enacted" in status["current_stage"].lower():
                # Search for corresponding public law in GovInfo
                govinfo_params = {
                    "api_key": GOVINFO_API_KEY,
                    "query": f"billNumber:{bill_number} AND congress:{congress}",
                    "collection": "PLAW",
                    "pageSize": 1
                }
                
                govinfo_response = await client.get("https://api.govinfo.gov/search", params=govinfo_params)
                if govinfo_response.status_code == 200:
                    govinfo_data = govinfo_response.json()
                    if govinfo_data.get("results"):
                        law_info = govinfo_data["results"][0]
            
            result = {
                "bill_id": f"{bill_type}{bill_number}-{congress}",
                "title": bill_info.get("title"),
                "sponsor": bill_info.get("sponsors", [{}])[0].get("fullName") if bill_info.get("sponsors") else None,
                "introduced_date": bill_info.get("introducedDate"),
                "progress": status,
                "key_dates": extract_key_dates(actions),
                "committee_history": extract_committee_history(actions),
                "vote_history": extract_vote_history(actions),
                "amendments_count": bill_info.get("amendmentsCount", 0),
                "cosponsors_count": bill_info.get("cosponsorsCount", 0),
                "public_law": law_info if law_info else None,
                "urls": {
                    "congress_gov": f"https://www.congress.gov/bill/{congress}th-congress/{format_bill_type(bill_type)}/{bill_number}",
                    "govtrack": f"https://www.govtrack.us/congress/bills/{congress}/{bill_type}{bill_number}"
                },
                "sources": [
                    format_source("congress", f"/v3/bill/{congress}/{bill_type}/{bill_number}"),
                    format_source("govinfo", "/search") if law_info else None
                ]
            }
        
        # Get Congress overview
        elif name == "get_congress_overview":
            congress = arguments.get("congress", 118)
            
            result = {
                "congress_number": congress,
                "years": get_congress_years(congress),
                "status": "Current" if congress == 118 else "Historical",
                "chambers": {
                    "house": {
                        "total_members": 435,
                        "majority_party": get_majority_party(congress, "house"),
                        "speaker": get_speaker(congress),
                        "committees_count": "20 standing committees"
                    },
                    "senate": {
                        "total_members": 100,
                        "majority_party": get_majority_party(congress, "senate"),
                        "president_pro_tempore": get_president_pro_tem(congress),
                        "committees_count": "16 standing committees"
                    }
                },
                "legislative_process": {
                    "bills_introduced": "Thousands per Congress",
                    "bills_enacted": "Typically 200-500 per Congress",
                    "success_rate": "Approximately 3-5% of bills become law"
                },
                "key_facts": [
                    f"The {congress}th Congress serves from {get_congress_years(congress)}",
                    "Each Congress lasts two years with two sessions",
                    "All bills must pass both chambers in identical form",
                    "The President must sign bills for them to become law (or Congress can override a veto)",
                    "Bills not enacted by the end of a Congress expire"
                ],
                "authoritative_sources": [
                    "Library of Congress - Congress.gov",
                    "U.S. Government Publishing Office - GovInfo.gov",
                    "Congressional Research Service",
                    "House.gov and Senate.gov"
                ],
                "source": format_source("congress", f"/v3/congress/{congress}")
            }
        
        # Explain legislative process
        elif name == "explain_legislative_process":
            topic = arguments.get("topic", "overview")
            
            explanations = {
                "overview": {
                    "title": "How the U.S. Legislative Process Works",
                    "description": "The legislative process is the method by which laws are created in the United States Congress.",
                    "key_steps": [
                        "1. Introduction: A bill is introduced in either the House or Senate",
                        "2. Committee Review: Bills are referred to relevant committees for study and hearings",
                        "3. Committee Action: Committees may amend, approve, or table bills",
                        "4. Floor Action: Bills approved by committee go to the full chamber for debate and voting",
                        "5. Other Chamber: Bills must pass both House and Senate in identical form",
                        "6. Conference Committee: Resolves differences between House and Senate versions",
                        "7. Presidential Action: President signs or vetoes the bill",
                        "8. Override: Congress can override a veto with 2/3 vote in both chambers"
                    ],
                    "important_notes": [
                        "Most bills die in committee without ever receiving a floor vote",
                        "Bills must be reintroduced in each new Congress if not enacted",
                        "The process is intentionally difficult to ensure careful consideration"
                    ]
                },
                "how a bill becomes law": {
                    "title": "How a Bill Becomes Law",
                    "description": "The journey from bill introduction to enacted law",
                    "detailed_process": [
                        "Idea/Drafting: Bills can originate from members, constituents, or interest groups",
                        "Sponsorship: A member of Congress must sponsor and introduce the bill",
                        "Committee Assignment: Bills are assigned to committees based on subject matter",
                        "Subcommittee Review: Often referred to specialized subcommittees first",
                        "Hearings: Committees hold hearings to gather expert testimony",
                        "Markup: Committee members debate and amend the bill",
                        "Committee Vote: Committee votes to report bill to full chamber",
                        "Rules Committee (House only): Sets terms for floor debate",
                        "Floor Debate: Full chamber debates the bill",
                        "Floor Vote: Requires simple majority to pass",
                        "Second Chamber: Entire process repeats in other chamber",
                        "Reconciliation: Differences resolved through conference committee",
                        "Final Passage: Both chambers pass identical version",
                        "Presidential Signature: Becomes law when President signs",
                        "Publication: Assigned public law number and published"
                    ]
                },
                "filibuster": {
                    "title": "The Senate Filibuster",
                    "description": "A procedural tactic to delay or prevent a vote in the Senate",
                    "key_points": [
                        "Unique to the Senate (not allowed in the House)",
                        "Senators can speak indefinitely to delay a vote",
                        "Requires 60 votes (3/5 of Senate) to invoke cloture and end debate",
                        "Does not apply to budget reconciliation bills",
                        "Has evolved from requiring actual continuous speaking to procedural threat",
                        "Major impact on legislative strategy and compromise"
                    ],
                    "history": "The filibuster is not in the Constitution but developed from Senate rules allowing unlimited debate"
                },
                "reconciliation": {
                    "title": "Budget Reconciliation Process",
                    "description": "Special expedited process for certain budget-related legislation",
                    "key_features": [
                        "Limited to bills affecting spending, revenue, and debt limit",
                        "Cannot be filibustered in the Senate (requires only 51 votes)",
                        "Subject to the Byrd Rule preventing non-budgetary provisions",
                        "Limited to once per fiscal year per topic (spending/revenue/debt)",
                        "20-hour debate limit in the Senate",
                        "Used for major legislation like tax reforms and healthcare changes"
                    ],
                    "limitations": "Cannot include provisions with no budgetary impact or that increase deficits beyond the budget window"
                },
                "committee process": {
                    "title": "Congressional Committee System",
                    "description": "Committees are the workhorses of Congress where most legislative work occurs",
                    "types": [
                        "Standing Committees: Permanent committees with specific jurisdictions",
                        "Select/Special Committees: Temporary committees for specific issues",
                        "Joint Committees: Include members from both House and Senate",
                        "Conference Committees: Resolve differences between House/Senate bills"
                    ],
                    "functions": [
                        "Review and amend legislation",
                        "Conduct oversight of executive agencies",
                        "Hold hearings and investigations",
                        "Control whether bills advance to floor votes"
                    ],
                    "power": "Committee chairs have significant power over which bills receive consideration"
                }
            }
            
            explanation = explanations.get(topic.lower(), explanations["overview"])
            
            result = {
                **explanation,
                "authoritative_note": "This information is based on official Congressional procedures as documented by the Congressional Research Service and official House and Senate rules.",
                "sources": [
                    "Congressional Research Service",
                    "House.gov - The Legislative Process",
                    "Senate.gov - Legislative Process",
                    "Constitution Article I"
                ]
            }
        
        # Get recent votes
        elif name == "get_recent_votes":
            chamber = arguments.get("chamber", "both")
            days = arguments.get("days", 7)
            limit = arguments.get("limit", 20)
            
            votes = []
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Get votes from requested chamber(s)
            chambers_to_check = ["house", "senate"] if chamber == "both" else [chamber]
            
            for ch in chambers_to_check:
                url = f"https://api.congress.gov/v3/{ch}-vote"
                headers = {"X-Api-Key": CONGRESS_API_KEY}
                params = {
                    "format": "json",
                    "limit": limit,
                    "fromDateTime": start_date.strftime("%Y-%m-%dT00:00:00Z"),
                    "toDateTime": end_date.strftime("%Y-%m-%dT23:59:59Z")
                }
                
                response = await client.get(url, headers=headers, params=params)
                if response.status_code == 200:
                    data = response.json()
                    chamber_votes = data.get("votes", [])
                    
                    for vote in chamber_votes:
                        votes.append({
                            "chamber": ch.capitalize(),
                            "date": vote.get("date"),
                            "roll_call": vote.get("rollCall"),
                            "question": vote.get("question"),
                            "result": vote.get("result"),
                            "bill": {
                                "number": vote.get("bill", {}).get("number"),
                                "title": vote.get("bill", {}).get("title")
                            } if vote.get("bill") else None,
                            "vote_counts": {
                                "yea": vote.get("yea"),
                                "nay": vote.get("nay"),
                                "present": vote.get("present"),
                                "not_voting": vote.get("notVoting")
                            },
                            "required": vote.get("required"),
                            "url": vote.get("url")
                        })
            
            # Sort by date
            votes.sort(key=lambda x: x.get("date", ""), reverse=True)
            
            result = {
                "period": {
                    "start": start_date.strftime("%Y-%m-%d"),
                    "end": end_date.strftime("%Y-%m-%d"),
                    "days": days
                },
                "chamber": chamber,
                "total_votes": len(votes),
                "votes": votes[:limit],
                "source": format_source("congress", "/v3/vote")
            }
        
        # Document Storage Tools
        elif name == "store_document":
            filename = arguments["filename"]
            content = arguments["content"]
            title = arguments.get("title", filename)
            description = arguments.get("description", "")
            tags = arguments.get("tags", "")
            category = arguments.get("category", "general")
            
            # Store the document
            doc_id = doc_store.store_document(
                filename=filename,
                content=content,
                title=title,
                description=description,
                tags=tags.split(",") if tags else [],
                category=category
            )
            
            result = {
                "document_id": doc_id,
                "filename": filename,
                "title": title,
                "status": "stored successfully",
                "source": "Document Storage System"
            }
        
        elif name == "search_documents":
            query = arguments.get("query", "")
            category = arguments.get("category")
            tags = arguments.get("tags", "").split(",") if arguments.get("tags") else None
            limit = arguments.get("limit", 10)
            
            # Search documents
            documents = doc_store.search_documents(
                query=query,
                category=category,
                tags=tags,
                limit=limit
            )
            
            result = {
                "query": query,
                "filters": {
                    "category": category,
                    "tags": tags
                },
                "results_count": len(documents),
                "documents": [
                    {
                        "id": doc["id"],
                        "title": doc["title"],
                        "filename": doc["filename"],
                        "description": doc["description"],
                        "category": doc["category"],
                        "tags": doc["tags"],
                        "uploaded_at": doc["uploaded_at"]
                    }
                    for doc in documents
                ],
                "source": "Document Storage System"
            }
        
        elif name == "get_document":
            document_id = arguments["document_id"]
            
            # Get the document
            document = doc_store.get_document(document_id)
            
            if document:
                result = {
                    "document": {
                        "id": document["id"],
                        "title": document["title"],
                        "filename": document["filename"],
                        "description": document["description"],
                        "category": document["category"],
                        "tags": document["tags"],
                        "content": document["content"],
                        "uploaded_at": document["uploaded_at"],
                        "size": document["size"]
                    },
                    "source": "Document Storage System"
                }
            else:
                result = {"error": f"Document '{document_id}' not found"}
        
        elif name == "list_documents":
            category = arguments.get("category")
            limit = arguments.get("limit", 20)
            
            # List documents using search_documents with no query
            documents = doc_store.search_documents(category=category)[:limit]
            
            result = {
                "filters": {"category": category},
                "total_count": len(documents),
                "documents": [
                    {
                        "id": doc["id"],
                        "title": doc["title"],
                        "filename": doc["filename"],
                        "description": doc["description"],
                        "category": doc["category"],
                        "tags": doc["tags"],
                        "uploaded_at": doc["uploaded_at"],
                        "size": doc["size"]
                    }
                    for doc in documents
                ],
                "source": "Document Storage System"
            }
        
        # Default response for unknown tools
        else:
            result = {"error": f"Tool '{name}' is not yet implemented"}
        
        # Cache and return result
        if result:
            result_text = json.dumps(result, indent=2)
            set_cache(cache_key, result_text)
            return [types.TextContent(type="text", text=result_text)]
        
    except httpx.HTTPStatusError as e:
        error_msg = {
            "error": f"API returned status {e.response.status_code}",
            "message": str(e),
            "tool": name,
            "note": "Please verify parameters and try again"
        }
        return [types.TextContent(type="text", text=json.dumps(error_msg, indent=2))]
    
    except Exception as e:
        error_msg = {
            "error": "An error occurred",
            "message": str(e),
            "tool": name,
            "note": "Please report this issue if it persists"
        }
        return [types.TextContent(type="text", text=json.dumps(error_msg, indent=2))]

# Helper functions
def format_bill_type(bill_type: str) -> str:
    """Format bill type for Congress.gov URLs"""
    mapping = {
        "hr": "house-bill",
        "s": "senate-bill",
        "hjres": "house-joint-resolution",
        "sjres": "senate-joint-resolution",
        "hconres": "house-concurrent-resolution",
        "sconres": "senate-concurrent-resolution",
        "hres": "house-resolution",
        "sres": "senate-resolution"
    }
    return mapping.get(bill_type.lower(), bill_type)

def determine_bill_status(bill_info: dict) -> str:
    """Determine the current status of a bill"""
    latest_action = bill_info.get("latestAction", {}).get("text", "").lower()
    
    if "became law" in latest_action or "became public law" in latest_action:
        return "Enacted - Became Law"
    elif "passed house and senate" in latest_action:
        return "Passed Both Chambers - Awaiting Presidential Action"
    elif "passed senate" in latest_action:
        return "Passed Senate - In House"
    elif "passed house" in latest_action:
        return "Passed House - In Senate"
    elif "reported" in latest_action:
        return "Reported from Committee"
    elif "referred to" in latest_action:
        return "In Committee"
    else:
        return "Introduced"

def analyze_bill_progress(bill_info: dict, actions: list) -> dict:
    """Analyze bill progress through legislative process"""
    stages = {
        "introduced": False,
        "committee": False,
        "reported": False,
        "passed_house": False,
        "passed_senate": False,
        "conference": False,
        "passed_both": False,
        "presented_to_president": False,
        "became_law": False
    }
    
    for action in actions:
        action_text = action.get("text", "").lower()
        
        if "introduced" in action_text:
            stages["introduced"] = True
        if "referred to" in action_text and "committee" in action_text:
            stages["committee"] = True
        if "reported" in action_text:
            stages["reported"] = True
        if "passed house" in action_text:
            stages["passed_house"] = True
        if "passed senate" in action_text:
            stages["passed_senate"] = True
        if "conference" in action_text:
            stages["conference"] = True
        if stages["passed_house"] and stages["passed_senate"]:
            stages["passed_both"] = True
        if "presented to president" in action_text:
            stages["presented_to_president"] = True
        if "became law" in action_text or "became public law" in action_text:
            stages["became_law"] = True
    
    # Determine current stage
    if stages["became_law"]:
        current = "Enacted - Became Law"
    elif stages["presented_to_president"]:
        current = "Awaiting Presidential Action"
    elif stages["passed_both"]:
        current = "Passed Both Chambers"
    elif stages["passed_senate"] and not stages["passed_house"]:
        current = "Passed Senate - In House"
    elif stages["passed_house"] and not stages["passed_senate"]:
        current = "Passed House - In Senate"
    elif stages["reported"]:
        current = "Reported from Committee"
    elif stages["committee"]:
        current = "In Committee"
    elif stages["introduced"]:
        current = "Introduced"
    else:
        current = "Pre-introduction"
    
    return {
        "current_stage": current,
        "stages_completed": stages,
        "progress_percentage": sum(stages.values()) / len(stages) * 100
    }

def extract_key_dates(actions: list) -> dict:
    """Extract key dates from bill actions"""
    dates = {}
    
    for action in actions:
        action_text = action.get("text", "").lower()
        action_date = action.get("actionDate")
        
        if "introduced" in action_text and "introduced" not in dates:
            dates["introduced"] = action_date
        if "referred to" in action_text and "committee" in action_text and "referred_to_committee" not in dates:
            dates["referred_to_committee"] = action_date
        if "reported" in action_text and "reported_from_committee" not in dates:
            dates["reported_from_committee"] = action_date
        if "passed house" in action_text and "passed_house" not in dates:
            dates["passed_house"] = action_date
        if "passed senate" in action_text and "passed_senate" not in dates:
            dates["passed_senate"] = action_date
        if "became law" in action_text and "became_law" not in dates:
            dates["became_law"] = action_date
    
    return dates

def extract_committee_history(actions: list) -> list:
    """Extract committee history from actions"""
    committees = []
    
    for action in actions:
        action_text = action.get("text", "")
        if "committee" in action_text.lower():
            committees.append({
                "date": action.get("actionDate"),
                "action": action_text,
                "chamber": action.get("chamber")
            })
    
    return committees[:10]  # Limit to 10 most recent

def extract_vote_history(actions: list) -> list:
    """Extract voting history from actions"""
    votes = []
    
    for action in actions:
        action_text = action.get("text", "").lower()
        if any(word in action_text for word in ["passed", "agreed to", "vote", "yea", "nay"]):
            if "vote" in action_text or "passed" in action_text:
                votes.append({
                    "date": action.get("actionDate"),
                    "action": action.get("text"),
                    "chamber": action.get("chamber")
                })
    
    return votes

def get_congress_years(congress: int) -> str:
    """Get the years for a given Congress number"""
    start_year = 1789 + (congress - 1) * 2
    end_year = start_year + 2
    return f"{start_year}-{end_year}"

def get_majority_party(congress: int, chamber: str) -> str:
    """Get majority party for a Congress and chamber"""
    # This would ideally come from an API or database
    # For now, return current known values
    if congress == 118:
        if chamber == "house":
            return "Republican"
        else:
            return "Democratic (with VP tiebreaker)"
    return "Historical data - consult Congress.gov"

def get_speaker(congress: int) -> str:
    """Get Speaker of the House for a Congress"""
    if congress == 118:
        return "Mike Johnson (R-LA)"
    return "Historical data - consult House.gov"

def get_president_pro_tem(congress: int) -> str:
    """Get President Pro Tempore for a Congress"""
    if congress == 118:
        return "Patty Murray (D-WA)"
    return "Historical data - consult Senate.gov"

async def run():
    """Run the server."""
    # Run the server using stdin/stdout
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="enactai-data",
                server_version="2.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(run())