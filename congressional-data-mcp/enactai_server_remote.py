#!/usr/bin/env python3
"""
EnactAI Data Remote MCP Server
Provides legislative data access via SSE transport for remote connections
"""

import os
import json
import asyncio
import httpx
import base64
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

# Import document store
from document_store import DocumentStore, load_default_documents

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

# Initialize document store
document_store = DocumentStore()

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
        ),
        types.Tool(
            name="get_related_bills",
            description="Find bills related to a specific bill (similar bills, procedurally-related bills, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "congress": {"type": "integer", "description": "Congress number"},
                    "bill_type": {"type": "string", "description": "Bill type (hr, s, hjres, sjres)"},
                    "bill_number": {"type": "integer", "description": "Bill number"},
                    "limit": {"type": "integer", "description": "Maximum results (default 20)"}
                },
                "required": ["congress", "bill_type", "bill_number"]
            }
        ),
        types.Tool(
            name="store_document",
            description="Store a document with metadata for later retrieval",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Document content (text or base64-encoded binary)"},
                    "filename": {"type": "string", "description": "Original filename"},
                    "title": {"type": "string", "description": "Document title"},
                    "description": {"type": "string", "description": "Document description"},
                    "category": {"type": "string", "description": "Category (e.g., 'legislative_process', 'rules', 'guides')"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for searching"},
                    "is_binary": {"type": "boolean", "description": "Whether content is base64-encoded binary", "default": False}
                },
                "required": ["content", "filename"]
            }
        ),
        types.Tool(
            name="search_documents",
            description="Search for stored documents by query, category, or tags",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query text"},
                    "category": {"type": "string", "description": "Filter by category"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Filter by tags"}
                }
            }
        ),
        types.Tool(
            name="get_document",
            description="Retrieve a specific document by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "doc_id": {"type": "string", "description": "Document ID"},
                    "include_content": {"type": "boolean", "description": "Include full document content", "default": False}
                },
                "required": ["doc_id"]
            }
        ),
        types.Tool(
            name="list_documents",
            description="List all stored documents with basic metadata",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Filter by category"},
                    "limit": {"type": "integer", "description": "Maximum results", "default": 50}
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
    
    elif name == "get_related_bills":
        try:
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
            
            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
            
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Error fetching related bills: {str(e)}"
            )]
    
    elif name == "store_document":
        try:
            content = arguments["content"]
            filename = arguments["filename"]
            is_binary = arguments.get("is_binary", False)
            
            # Decode content if binary
            if is_binary:
                content_bytes = base64.b64decode(content)
            else:
                content_bytes = content.encode('utf-8')
            
            # Store the document
            doc_id = document_store.store_document(
                content=content_bytes,
                filename=filename,
                title=arguments.get("title"),
                description=arguments.get("description"),
                category=arguments.get("category"),
                tags=arguments.get("tags"),
                metadata=arguments.get("metadata")
            )
            
            result = {
                "status": "success",
                "doc_id": doc_id,
                "message": f"Document '{filename}' stored successfully",
                "source": format_source("calculation", "Document Storage")
            }
            
            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
            
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Error storing document: {str(e)}"
            )]
    
    elif name == "search_documents":
        try:
            results = document_store.search_documents(
                query=arguments.get("query"),
                category=arguments.get("category"),
                tags=arguments.get("tags")
            )
            
            response_data = {
                "results": results,
                "count": len(results),
                "source": format_source("calculation", "Document Search")
            }
            
            return [types.TextContent(
                type="text",
                text=json.dumps(response_data, indent=2)
            )]
            
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Error searching documents: {str(e)}"
            )]
    
    elif name == "get_document":
        try:
            doc_id = arguments["doc_id"]
            include_content = arguments.get("include_content", False)
            
            doc = document_store.get_document(doc_id)
            if not doc:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "error": "Document not found",
                        "doc_id": doc_id
                    }, indent=2)
                )]
            
            # Include content if requested
            if include_content:
                content_bytes = document_store.get_document_content(doc_id)
                if content_bytes:
                    # Try to decode as text, otherwise encode as base64
                    try:
                        doc["content"] = content_bytes.decode('utf-8')
                        doc["content_encoding"] = "text"
                    except:
                        doc["content"] = base64.b64encode(content_bytes).decode('ascii')
                        doc["content_encoding"] = "base64"
            
            doc["source"] = format_source("calculation", "Document Storage")
            
            return [types.TextContent(
                type="text",
                text=json.dumps(doc, indent=2)
            )]
            
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Error retrieving document: {str(e)}"
            )]
    
    elif name == "list_documents":
        try:
            category = arguments.get("category")
            limit = arguments.get("limit", 50)
            
            # Search with optional category filter
            results = document_store.search_documents(category=category)
            
            # Limit results
            results = results[:limit]
            
            # Get categories list
            categories = document_store.list_categories()
            
            response_data = {
                "documents": results,
                "count": len(results),
                "categories": categories,
                "source": format_source("calculation", "Document Storage")
            }
            
            return [types.TextContent(
                type="text",
                text=json.dumps(response_data, indent=2)
            )]
            
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Error listing documents: {str(e)}"
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
    
    elif name == "get_member":
        try:
            bioguide_id = arguments["bioguide_id"]
            
            url = f"https://api.congress.gov/v3/member/{bioguide_id}"
            headers = {"X-Api-Key": CONGRESS_API_KEY}
            params = {"format": "json"}
            
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            member = data.get("member", {})
            
            result = {
                "bioguide_id": bioguide_id,
                "name": member.get("directOrderName"),
                "state": member.get("state"),
                "party": member.get("partyName"),
                "chamber": "Senate" if member.get("terms", [{}])[-1].get("chamber") == "Senate" else "House",
                "district": member.get("district"),
                "terms": member.get("terms", []),
                "current_role": member.get("terms", [{}])[-1] if member.get("terms") else {},
                "depiction": member.get("depiction", {}).get("imageUrl"),
                "source": format_source("congress", f"Member {bioguide_id}")
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
    
    elif name == "search_members":
        try:
            state = arguments.get("state")
            party = arguments.get("party")
            chamber = arguments.get("chamber")
            current_only = arguments.get("current_only", True)
            
            # Build URL based on chamber
            if chamber == "house":
                url = "https://api.congress.gov/v3/member/house"
            elif chamber == "senate":
                url = "https://api.congress.gov/v3/member/senate"
            else:
                url = "https://api.congress.gov/v3/member"
            
            if state:
                url += f"/{state}"
            
            if current_only:
                url += "/current"
            
            headers = {"X-Api-Key": CONGRESS_API_KEY}
            params = {"format": "json", "limit": 250}
            
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            members = data.get("members", [])
            
            # Filter by party if specified
            if party:
                members = [m for m in members if m.get("partyName", "")[0] == party]
            
            results = []
            for member in members:
                results.append({
                    "bioguide_id": member.get("bioguideId"),
                    "name": member.get("name"),
                    "state": member.get("state"),
                    "party": member.get("partyName"),
                    "district": member.get("district"),
                    "url": member.get("url")
                })
            
            response_data = {
                "results": results,
                "count": len(results),
                "source": format_source("congress", "Member Search")
            }
            
            return [types.TextContent(
                type="text",
                text=json.dumps(response_data, indent=2)
            )]
            
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Error searching members: {str(e)}"
            )]
    
    elif name == "get_committee":
        try:
            chamber = arguments["chamber"]
            committee_code = arguments["committee_code"]
            
            url = f"https://api.congress.gov/v3/committee/{chamber}/{committee_code}"
            headers = {"X-Api-Key": CONGRESS_API_KEY}
            params = {"format": "json"}
            
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            committee = data.get("committee", {})
            
            result = {
                "committee_code": committee_code,
                "name": committee.get("name"),
                "chamber": committee.get("chamber"),
                "type": committee.get("type"),
                "jurisdiction": committee.get("jurisdiction"),
                "url": committee.get("url"),
                "subcommittees": committee.get("subcommittees", {}).get("item", []),
                "source": format_source("congress", f"Committee {committee_code}")
            }
            
            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
            
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Error fetching committee: {str(e)}"
            )]
    
    elif name == "get_vote":
        try:
            congress = arguments["congress"]
            chamber = arguments["chamber"]
            session = arguments["session"]
            roll_call = arguments["roll_call"]
            
            url = f"https://api.congress.gov/v3/{chamber}/vote/{congress}/{session}/{roll_call}"
            headers = {"X-Api-Key": CONGRESS_API_KEY}
            params = {"format": "json"}
            
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            vote = data.get("vote", {})
            
            result = {
                "congress": congress,
                "chamber": chamber,
                "session": session,
                "roll_call": roll_call,
                "date": vote.get("date"),
                "question": vote.get("question"),
                "result": vote.get("result"),
                "vote_type": vote.get("voteType"),
                "required": vote.get("required"),
                "counts": vote.get("counts"),
                "bill": vote.get("bill") if vote.get("bill") else None,
                "source": format_source("congress", f"Vote {chamber}/{congress}/{session}/{roll_call}")
            }
            
            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
            
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Error fetching vote: {str(e)}"
            )]
    
    elif name == "search_govinfo":
        try:
            query = arguments["query"]
            collection = arguments.get("collection")
            date_from = arguments.get("date_from")
            date_to = arguments.get("date_to")
            limit = arguments.get("limit", 20)
            
            url = "https://api.govinfo.gov/search"
            headers = {"X-Api-Key": GOVINFO_API_KEY if GOVINFO_API_KEY else ""}
            
            params = {
                "query": query,
                "pageSize": limit,
                "offsetMark": "*"
            }
            
            if collection:
                params["collection"] = collection
            if date_from:
                params["publishedDateFrom"] = date_from
            if date_to:
                params["publishedDateTo"] = date_to
            
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for doc in data.get("results", []):
                results.append({
                    "title": doc.get("title"),
                    "packageId": doc.get("packageId"),
                    "lastModified": doc.get("lastModified"),
                    "packageLink": doc.get("packageLink"),
                    "docClass": doc.get("docClass"),
                    "congress": doc.get("congress")
                })
            
            response_data = {
                "results": results,
                "count": data.get("count", len(results)),
                "source": format_source("govinfo", "GovInfo Search")
            }
            
            return [types.TextContent(
                type="text",
                text=json.dumps(response_data, indent=2)
            )]
            
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Error searching GovInfo: {str(e)}"
            )]
    
    elif name == "get_public_law":
        try:
            congress = arguments["congress"]
            law_number = arguments["law_number"]
            
            # Format: PLAW-{congress}publ{law_number}
            package_id = f"PLAW-{congress}publ{law_number}"
            
            url = f"https://api.govinfo.gov/packages/{package_id}/summary"
            headers = {"X-Api-Key": GOVINFO_API_KEY if GOVINFO_API_KEY else ""}
            
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            
            result = {
                "congress": congress,
                "law_number": law_number,
                "title": data.get("title"),
                "packageId": data.get("packageId"),
                "dateIssued": data.get("dateIssued"),
                "detailsLink": data.get("detailsLink"),
                "related_bills": data.get("references", {}).get("billNumber", []),
                "source": format_source("govinfo", f"Public Law {congress}-{law_number}")
            }
            
            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
            
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Error fetching public law: {str(e)}"
            )]
    
    elif name == "get_congressional_record":
        try:
            date = arguments["date"]
            section = arguments.get("section")
            keywords = arguments.get("keywords")
            
            # Format date for API (YYYY-MM-DD)
            url = "https://api.govinfo.gov/search"
            headers = {"X-Api-Key": GOVINFO_API_KEY if GOVINFO_API_KEY else ""}
            
            query = f"collection:CREC AND publishdate:{date}"
            if section:
                query += f" AND section:{section}"
            if keywords:
                query += f" AND {keywords}"
            
            params = {
                "query": query,
                "pageSize": 50,
                "offsetMark": "*"
            }
            
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for doc in data.get("results", []):
                results.append({
                    "title": doc.get("title"),
                    "packageId": doc.get("packageId"),
                    "granuleId": doc.get("granuleId"),
                    "section": doc.get("section"),
                    "speaker": doc.get("speaker"),
                    "detailsLink": doc.get("detailsLink")
                })
            
            response_data = {
                "date": date,
                "results": results,
                "count": len(results),
                "source": format_source("govinfo", f"Congressional Record {date}")
            }
            
            return [types.TextContent(
                type="text",
                text=json.dumps(response_data, indent=2)
            )]
            
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Error fetching Congressional Record: {str(e)}"
            )]
    
    elif name == "get_member_votes":
        try:
            bioguide_id = arguments["bioguide_id"]
            congress = arguments.get("congress", 118)
            limit = arguments.get("limit", 50)
            
            # Get member's voting positions
            url = f"https://api.congress.gov/v3/member/{bioguide_id}/voting-record"
            headers = {"X-Api-Key": CONGRESS_API_KEY}
            params = {
                "format": "json",
                "limit": limit
            }
            
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            votes = data.get("votes", [])
            
            results = []
            for vote in votes:
                results.append({
                    "congress": vote.get("congress"),
                    "chamber": vote.get("chamber"),
                    "rollCall": vote.get("rollCall"),
                    "date": vote.get("date"),
                    "question": vote.get("question"),
                    "position": vote.get("position"),
                    "result": vote.get("result"),
                    "bill": vote.get("bill") if vote.get("bill") else None
                })
            
            response_data = {
                "bioguide_id": bioguide_id,
                "votes": results,
                "count": len(results),
                "source": format_source("congress", f"Member {bioguide_id} Voting Record")
            }
            
            return [types.TextContent(
                type="text",
                text=json.dumps(response_data, indent=2)
            )]
            
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Error fetching member votes: {str(e)}"
            )]
    
    elif name == "get_congress_calendar":
        try:
            chamber = arguments.get("chamber", "both")
            date_from = arguments.get("date_from")
            date_to = arguments.get("date_to")
            
            # Note: Congress.gov API doesn't have a direct calendar endpoint
            # This would typically integrate with House/Senate calendar systems
            # For now, return educational information about the calendar
            
            calendar_info = {
                "chamber": chamber,
                "typical_schedule": {
                    "house": {
                        "voting_days": "Tuesday through Thursday",
                        "first_votes": "6:30 PM Monday, 2:00 PM Tuesday-Wednesday, 9:00 AM Thursday-Friday",
                        "last_votes": "No later than 3:00 PM Friday"
                    },
                    "senate": {
                        "voting_days": "Monday through Friday",
                        "typical_hours": "Convenes at 10:00 AM or 2:00 PM",
                        "voting_windows": "Votes typically occur in afternoon"
                    }
                },
                "recess_periods": [
                    "Presidents Day (February)",
                    "Two-week Spring Recess (March/April)",
                    "Memorial Day (May)",
                    "Independence Day (July)",
                    "August Recess (entire month)",
                    "Labor Day (September)",
                    "Columbus Day (October)",
                    "Thanksgiving (November)",
                    "Christmas/New Year (December/January)"
                ],
                "note": "Check house.gov and senate.gov for current calendars",
                "source": format_source("calculation", "Congressional Calendar Information")
            }
            
            return [types.TextContent(
                type="text",
                text=json.dumps(calendar_info, indent=2)
            )]
            
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Error fetching calendar: {str(e)}"
            )]
    
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
    # Load default documents on startup
    print("Loading default Congressional knowledge documents...")
    load_default_documents()
    
    # Run with uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)