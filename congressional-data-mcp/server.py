#!/usr/bin/env python3
"""
Congressional Data MCP Server
Combines Congress.gov API and GovInfo API into a unified MCP interface
"""

import os
import asyncio
import json
import hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

import httpx

# Try to load optional dependencies
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Environment variables should be set externally

import structlog
from aiolimiter import AsyncLimiter

# Try to import cache, but work without it if not available
try:
    from aiocache import Cache
    from aiocache.serializers import JsonSerializer
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    Cache = None
    JsonSerializer = None

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.session import InitializationOptions
from mcp.types import Tool, TextContent
from mcp.shared.exceptions import McpError

# Configure structured logging to stderr only (stdout is for MCP protocol)
import sys
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger()

# API Configuration
CONGRESS_API_KEY = os.getenv("CONGRESS_GOV_API_KEY")
GOVINFO_API_KEY = os.getenv("GOVINFO_API_KEY")
CONGRESS_BASE_URL = "https://api.congress.gov/v3"
GOVINFO_BASE_URL = "https://api.govinfo.gov"

# Cache Configuration
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))
CACHE_SIZE = int(os.getenv("CACHE_SIZE", "1000"))
ENABLE_CACHING = os.getenv("ENABLE_CACHING", "true").lower() == "true"

# Rate Limiting Configuration
RATE_LIMIT_CONGRESS = int(os.getenv("RATE_LIMIT_CONGRESS", "100"))
RATE_LIMIT_GOVINFO = int(os.getenv("RATE_LIMIT_GOVINFO", "100"))
ENABLE_RATE_LIMITING = os.getenv("ENABLE_RATE_LIMITING", "true").lower() == "true"

# Initialize server
server = Server("congressional-data-mcp")

# HTTP client with retries
client = httpx.AsyncClient(
    timeout=httpx.Timeout(30.0),
    limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
    follow_redirects=True
)

# Initialize cache (if available)
if CACHE_AVAILABLE:
    cache = Cache(Cache.MEMORY, serializer=JsonSerializer(), namespace="congress_mcp")
else:
    cache = None

# Initialize rate limiters (per minute)
congress_limiter = AsyncLimiter(RATE_LIMIT_CONGRESS, 60)
govinfo_limiter = AsyncLimiter(RATE_LIMIT_GOVINFO, 60)

# Helper functions
def get_cache_key(prefix: str, endpoint: str, params: Dict[str, Any] = None) -> str:
    """Generate cache key from request parameters"""
    key_parts = [prefix, endpoint]
    if params:
        # Sort params for consistent keys
        sorted_params = sorted(params.items())
        params_str = json.dumps(sorted_params)
        key_parts.append(hashlib.md5(params_str.encode()).hexdigest())
    return ":".join(key_parts)

async def make_congress_request(endpoint: str, params: Dict[str, Any] = None) -> Dict:
    """Make authenticated request to Congress.gov API with caching and rate limiting"""
    if not CONGRESS_API_KEY:
        raise McpError("CONGRESS_GOV_API_KEY not configured")
    
    # Check cache first
    cache_key = get_cache_key("congress", endpoint, params)
    if ENABLE_CACHING and cache:
        cached_result = await cache.get(cache_key)
        if cached_result:
            logger.info("cache_hit", api="congress", endpoint=endpoint)
            return cached_result
    
    # Apply rate limiting
    if ENABLE_RATE_LIMITING:
        async with congress_limiter:
            pass  # Rate limiter will delay if necessary
    
    headers = {"X-Api-Key": CONGRESS_API_KEY}
    if params is None:
        params = {}
    params["format"] = "json"
    
    url = f"{CONGRESS_BASE_URL}{endpoint}"
    
    # Retry logic
    max_retries = int(os.getenv("MAX_RETRIES", "3"))
    retry_delay = int(os.getenv("RETRY_DELAY", "1"))
    
    for attempt in range(max_retries):
        try:
            logger.info("api_request", api="congress", endpoint=endpoint, attempt=attempt+1)
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            result = response.json()
            
            # Cache successful result
            if ENABLE_CACHING and cache:
                await cache.set(cache_key, result, ttl=CACHE_TTL)
            
            return result
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:  # Rate limited
                logger.warning("rate_limited", api="congress", endpoint=endpoint)
                await asyncio.sleep(retry_delay * (attempt + 1))
            elif e.response.status_code >= 500 and attempt < max_retries - 1:
                logger.warning("server_error", api="congress", endpoint=endpoint, status=e.response.status_code)
                await asyncio.sleep(retry_delay)
            else:
                raise
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning("request_error", api="congress", endpoint=endpoint, error=str(e))
                await asyncio.sleep(retry_delay)
            else:
                raise

async def make_govinfo_request(endpoint: str, params: Dict[str, Any] = None) -> Dict:
    """Make authenticated request to GovInfo API with caching and rate limiting"""
    if not GOVINFO_API_KEY:
        raise McpError("GOVINFO_API_KEY not configured")
    
    # Check cache first
    cache_key = get_cache_key("govinfo", endpoint, params)
    if ENABLE_CACHING:
        cached_result = await cache.get(cache_key)
        if cached_result:
            logger.info("cache_hit", api="govinfo", endpoint=endpoint)
            return cached_result
    
    # Apply rate limiting
    if ENABLE_RATE_LIMITING:
        async with govinfo_limiter:
            pass  # Rate limiter will delay if necessary
    
    if params is None:
        params = {}
    params["api_key"] = GOVINFO_API_KEY
    
    url = f"{GOVINFO_BASE_URL}{endpoint}"
    
    # Retry logic
    max_retries = int(os.getenv("MAX_RETRIES", "3"))
    retry_delay = int(os.getenv("RETRY_DELAY", "1"))
    
    for attempt in range(max_retries):
        try:
            logger.info("api_request", api="govinfo", endpoint=endpoint, attempt=attempt+1)
            response = await client.get(url, params=params)
            
            # Handle GovInfo's 503 with Retry-After header
            if response.status_code == 503 and "Retry-After" in response.headers:
                retry_after = int(response.headers["Retry-After"])
                logger.info("govinfo_retry_after", seconds=retry_after)
                await asyncio.sleep(retry_after)
                continue
            
            response.raise_for_status()
            result = response.json()
            
            # Cache successful result
            if ENABLE_CACHING and cache:
                await cache.set(cache_key, result, ttl=CACHE_TTL)
            
            return result
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:  # Rate limited
                logger.warning("rate_limited", api="govinfo", endpoint=endpoint)
                await asyncio.sleep(retry_delay * (attempt + 1))
            elif e.response.status_code >= 500 and attempt < max_retries - 1:
                logger.warning("server_error", api="govinfo", endpoint=endpoint, status=e.response.status_code)
                await asyncio.sleep(retry_delay)
            else:
                raise
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning("request_error", api="govinfo", endpoint=endpoint, error=str(e))
                await asyncio.sleep(retry_delay)
            else:
                raise

# Congress.gov API Tools
@server.list_tools()
async def list_tools() -> List[Tool]:
    """List all available tools"""
    return [
        # Congress.gov Tools
        Tool(
            name="get_bills",
            description="Retrieve bills from Congress.gov API with filtering options",
            inputSchema={
                "type": "object",
                "properties": {
                    "congress": {"type": "integer", "description": "Congress number (e.g., 118)"},
                    "bill_type": {"type": "string", "description": "Type: hr, s, hjres, sjres, hconres, sconres, hres, sres"},
                    "bill_number": {"type": "integer", "description": "Specific bill number"},
                    "limit": {"type": "integer", "description": "Max results (1-250)", "default": 20},
                    "offset": {"type": "integer", "description": "Starting record", "default": 0},
                    "from_datetime": {"type": "string", "description": "Start date (YYYY-MM-DDTHH:MM:SSZ)"},
                    "to_datetime": {"type": "string", "description": "End date (YYYY-MM-DDTHH:MM:SSZ)"},
                    "sort": {"type": "string", "description": "Sort order", "default": "updateDate+desc"}
                }
            }
        ),
        Tool(
            name="get_bill_details",
            description="Get detailed information about a specific bill including actions, cosponsors, text",
            inputSchema={
                "type": "object",
                "required": ["congress", "bill_type", "bill_number"],
                "properties": {
                    "congress": {"type": "integer", "description": "Congress number"},
                    "bill_type": {"type": "string", "description": "Bill type"},
                    "bill_number": {"type": "integer", "description": "Bill number"},
                    "include": {"type": "array", "items": {"type": "string"}, 
                               "description": "Include: actions, amendments, committees, cosponsors, relatedbills, subjects, summaries, text, titles"}
                }
            }
        ),
        Tool(
            name="get_members",
            description="Retrieve member information from Congress",
            inputSchema={
                "type": "object",
                "properties": {
                    "bioguide_id": {"type": "string", "description": "Specific member bioguide ID"},
                    "current_member": {"type": "boolean", "description": "Filter current members only"},
                    "state": {"type": "string", "description": "State abbreviation"},
                    "district": {"type": "integer", "description": "House district number"},
                    "party": {"type": "string", "description": "Party affiliation"},
                    "limit": {"type": "integer", "default": 20},
                    "offset": {"type": "integer", "default": 0}
                }
            }
        ),
        Tool(
            name="get_votes",
            description="Retrieve voting records from House or Senate",
            inputSchema={
                "type": "object",
                "properties": {
                    "chamber": {"type": "string", "description": "house or senate", "enum": ["house", "senate"]},
                    "congress": {"type": "integer", "description": "Congress number"},
                    "session": {"type": "integer", "description": "Session number (1 or 2)"},
                    "roll_call": {"type": "integer", "description": "Specific roll call number"},
                    "limit": {"type": "integer", "default": 20},
                    "offset": {"type": "integer", "default": 0}
                }
            }
        ),
        Tool(
            name="get_committees",
            description="Get committee information and activities",
            inputSchema={
                "type": "object",
                "properties": {
                    "chamber": {"type": "string", "description": "house, senate, or joint"},
                    "committee_code": {"type": "string", "description": "Committee code"},
                    "include_subcommittees": {"type": "boolean", "default": True},
                    "limit": {"type": "integer", "default": 20},
                    "offset": {"type": "integer", "default": 0}
                }
            }
        ),
        
        # GovInfo Tools
        Tool(
            name="govinfo_search",
            description="Search GovInfo for government documents",
            inputSchema={
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "collection": {"type": "string", "description": "Collection code (BILLS, PLAW, FR, CFR, etc.)"},
                    "congress": {"type": "integer", "description": "Filter by Congress"},
                    "docClass": {"type": "string", "description": "Document class"},
                    "dateIssuedFrom": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                    "dateIssuedTo": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                    "pageSize": {"type": "integer", "default": 20, "maximum": 100},
                    "offsetMark": {"type": "string", "description": "Pagination cursor"}
                }
            }
        ),
        Tool(
            name="govinfo_get_package",
            description="Get detailed package information from GovInfo",
            inputSchema={
                "type": "object",
                "required": ["packageId"],
                "properties": {
                    "packageId": {"type": "string", "description": "Package ID (e.g., BILLS-118hr1234ih)"},
                    "include_content": {"type": "boolean", "default": False, "description": "Include full content"},
                    "content_type": {"type": "string", "enum": ["pdf", "xml", "htm", "txt"], "default": "xml"}
                }
            }
        ),
        Tool(
            name="govinfo_get_collection",
            description="List packages in a GovInfo collection within date range",
            inputSchema={
                "type": "object",
                "required": ["collection"],
                "properties": {
                    "collection": {"type": "string", "description": "Collection code"},
                    "startDate": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                    "endDate": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                    "pageSize": {"type": "integer", "default": 20},
                    "offset": {"type": "integer", "default": 0}
                }
            }
        ),
        Tool(
            name="govinfo_get_related",
            description="Get related documents from GovInfo",
            inputSchema={
                "type": "object",
                "required": ["packageId"],
                "properties": {
                    "packageId": {"type": "string", "description": "Package ID"},
                    "relationship_type": {"type": "string", "description": "Type of relationship"}
                }
            }
        ),
        Tool(
            name="get_public_laws",
            description="Get public laws with full text and metadata",
            inputSchema={
                "type": "object",
                "properties": {
                    "congress": {"type": "integer", "description": "Congress number"},
                    "law_number": {"type": "integer", "description": "Public law number"},
                    "from_date": {"type": "string", "description": "Start date"},
                    "to_date": {"type": "string", "description": "End date"},
                    "limit": {"type": "integer", "default": 20}
                }
            }
        ),
        Tool(
            name="get_federal_register",
            description="Search Federal Register documents",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "agency": {"type": "string", "description": "Issuing agency"},
                    "doc_type": {"type": "string", "description": "Document type (rule, proposed_rule, notice, presidential_document)"},
                    "from_date": {"type": "string", "description": "Start date"},
                    "to_date": {"type": "string", "description": "End date"},
                    "limit": {"type": "integer", "default": 20}
                }
            }
        ),
        Tool(
            name="get_cfr",
            description="Get Code of Federal Regulations sections",
            inputSchema={
                "type": "object",
                "required": ["title", "part"],
                "properties": {
                    "title": {"type": "integer", "description": "CFR title number"},
                    "part": {"type": "integer", "description": "CFR part number"},
                    "section": {"type": "string", "description": "Specific section"},
                    "year": {"type": "integer", "description": "Year of CFR edition"}
                }
            }
        ),
        Tool(
            name="track_legislation",
            description="Track legislation from introduction to law across both systems",
            inputSchema={
                "type": "object",
                "required": ["congress", "bill_type", "bill_number"],
                "properties": {
                    "congress": {"type": "integer", "description": "Congress number"},
                    "bill_type": {"type": "string", "description": "Bill type"},
                    "bill_number": {"type": "integer", "description": "Bill number"}
                }
            }
        )
    ]

# Tool implementations
@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls"""
    try:
        # Congress.gov tools
        if name == "get_bills":
            endpoint = "/bill"
            if arguments.get("congress"):
                endpoint += f"/{arguments['congress']}"
                if arguments.get("bill_type"):
                    endpoint += f"/{arguments['bill_type']}"
                    if arguments.get("bill_number"):
                        endpoint += f"/{arguments['bill_number']}"
            
            params = {k: v for k, v in arguments.items() 
                     if k in ["limit", "offset", "from_datetime", "to_datetime", "sort"] and v is not None}
            
            result = await make_congress_request(endpoint, params)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "get_bill_details":
            congress = arguments["congress"]
            bill_type = arguments["bill_type"]
            bill_number = arguments["bill_number"]
            base_endpoint = f"/bill/{congress}/{bill_type}/{bill_number}"
            
            result = {"bill": await make_congress_request(base_endpoint)}
            
            # Include additional data if requested
            if "include" in arguments:
                for item in arguments["include"]:
                    if item in ["actions", "amendments", "committees", "cosponsors", 
                               "relatedbills", "subjects", "summaries", "text", "titles"]:
                        result[item] = await make_congress_request(f"{base_endpoint}/{item}")
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "get_members":
            endpoint = "/member"
            if arguments.get("bioguide_id"):
                endpoint += f"/{arguments['bioguide_id']}"
            
            params = {k: v for k, v in arguments.items() 
                     if k not in ["bioguide_id"] and v is not None}
            
            result = await make_congress_request(endpoint, params)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "get_votes":
            chamber = arguments.get("chamber", "house")
            endpoint = f"/{chamber}-vote"
            
            if arguments.get("congress"):
                endpoint += f"/{arguments['congress']}"
                if arguments.get("session"):
                    endpoint += f"/{arguments['session']}"
                    if arguments.get("roll_call"):
                        endpoint += f"/{arguments['roll_call']}"
            
            params = {k: v for k, v in arguments.items() 
                     if k in ["limit", "offset"] and v is not None}
            
            result = await make_congress_request(endpoint, params)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "get_committees":
            endpoint = "/committee"
            params = {k: v for k, v in arguments.items() if v is not None}
            
            result = await make_congress_request(endpoint, params)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        # GovInfo tools
        elif name == "govinfo_search":
            endpoint = "/search"
            params = {k: v for k, v in arguments.items() if v is not None}
            
            result = await make_govinfo_request(endpoint, params)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "govinfo_get_package":
            package_id = arguments["packageId"]
            endpoint = f"/packages/{package_id}/summary"
            
            result = await make_govinfo_request(endpoint)
            
            if arguments.get("include_content"):
                content_type = arguments.get("content_type", "xml")
                content_endpoint = f"/packages/{package_id}/{content_type}"
                try:
                    content_response = await client.get(
                        f"{GOVINFO_BASE_URL}{content_endpoint}",
                        params={"api_key": GOVINFO_API_KEY}
                    )
                    if content_response.status_code == 200:
                        result["content"] = content_response.text
                except Exception as e:
                    result["content_error"] = str(e)
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "govinfo_get_collection":
            collection = arguments["collection"]
            start_date = arguments.get("startDate", "2024-01-01")
            end_date = arguments.get("endDate", datetime.now().strftime("%Y-%m-%d"))
            
            endpoint = f"/collections/{collection}/{start_date}T00:00:00Z/{end_date}T23:59:59Z"
            params = {
                "pageSize": arguments.get("pageSize", 20),
                "offset": arguments.get("offset", 0)
            }
            
            result = await make_govinfo_request(endpoint, params)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "govinfo_get_related":
            package_id = arguments["packageId"]
            endpoint = f"/packages/{package_id}/related"
            
            result = await make_govinfo_request(endpoint)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "get_public_laws":
            # Use GovInfo to get public laws
            params = {
                "query": f"collection:PLAW",
                "pageSize": arguments.get("limit", 20)
            }
            
            if arguments.get("congress"):
                params["query"] += f" AND congress:{arguments['congress']}"
            if arguments.get("law_number"):
                params["query"] += f" AND lawNumber:{arguments['law_number']}"
            if arguments.get("from_date"):
                params["dateIssuedFrom"] = arguments["from_date"]
            if arguments.get("to_date"):
                params["dateIssuedTo"] = arguments["to_date"]
            
            result = await make_govinfo_request("/search", params)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "get_federal_register":
            params = {
                "collection": "FR",
                "pageSize": arguments.get("limit", 20)
            }
            
            query_parts = []
            if arguments.get("query"):
                query_parts.append(arguments["query"])
            if arguments.get("agency"):
                query_parts.append(f"agency:\"{arguments['agency']}\"")
            if arguments.get("doc_type"):
                query_parts.append(f"doctype:{arguments['doc_type']}")
            
            if query_parts:
                params["query"] = " AND ".join(query_parts)
            
            if arguments.get("from_date"):
                params["dateIssuedFrom"] = arguments["from_date"]
            if arguments.get("to_date"):
                params["dateIssuedTo"] = arguments["to_date"]
            
            result = await make_govinfo_request("/search", params)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "get_cfr":
            title = arguments["title"]
            part = arguments["part"]
            year = arguments.get("year", datetime.now().year)
            
            query = f"collection:CFR AND title:{title} AND part:{part}"
            if arguments.get("section"):
                query += f" AND section:{arguments['section']}"
            
            params = {
                "query": query,
                "pageSize": 20
            }
            
            result = await make_govinfo_request("/search", params)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "track_legislation":
            congress = arguments["congress"]
            bill_type = arguments["bill_type"]
            bill_number = arguments["bill_number"]
            
            # Get bill info from Congress.gov
            bill_endpoint = f"/bill/{congress}/{bill_type}/{bill_number}"
            bill_data = await make_congress_request(bill_endpoint)
            
            # Get actions
            actions_data = await make_congress_request(f"{bill_endpoint}/actions")
            
            # Check if it became law
            result = {
                "bill": bill_data,
                "actions": actions_data,
                "status": "pending"
            }
            
            # Search for corresponding public law in GovInfo
            if bill_data.get("bill", {}).get("policyArea"):
                govinfo_params = {
                    "query": f"collection:PLAW AND congress:{congress} AND billNumber:{bill_number}",
                    "pageSize": 5
                }
                
                try:
                    law_data = await make_govinfo_request("/search", govinfo_params)
                    if law_data.get("results"):
                        result["public_law"] = law_data["results"][0]
                        result["status"] = "enacted"
                except:
                    pass
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]

async def main():
    """Run the MCP server"""
    # Initialize cache if using Redis
    redis_host = os.getenv("REDIS_HOST")
    if redis_host and ENABLE_CACHING:
        try:
            global cache
            cache = Cache(
                Cache.REDIS,
                endpoint=redis_host,
                port=int(os.getenv("REDIS_PORT", "6379")),
                password=os.getenv("REDIS_PASSWORD"),
                serializer=JsonSerializer(),
                namespace="congress_mcp"
            )
            logger.info("cache_initialized", backend="redis")
        except Exception as e:
            logger.warning("redis_connection_failed", error=str(e))
            logger.info("falling_back_to_memory_cache")
    
    # Check if running in Docker health check mode
    docker_mode = os.getenv("DOCKER_MODE", "false").lower() == "true"
    
    # Start optional HTTP health check server (only in Docker mode)
    if docker_mode:
        try:
            from aiohttp import web
            
            async def health_check(request):
                return web.json_response({"status": "healthy", "service": "congressional-data-mcp"})
            
            async def metrics(request):
                # Basic metrics endpoint
                metrics_data = f"""# HELP mcp_requests_total Total number of MCP requests
# TYPE mcp_requests_total counter
mcp_requests_total{{service="congressional-data-mcp"}} 0

# HELP mcp_cache_hits_total Total number of cache hits
# TYPE mcp_cache_hits_total counter
mcp_cache_hits_total{{service="congressional-data-mcp"}} 0

# HELP mcp_api_requests_total Total number of API requests
# TYPE mcp_api_requests_total counter
mcp_api_requests_total{{api="congress"}} 0
mcp_api_requests_total{{api="govinfo"}} 0
"""
                return web.Response(text=metrics_data, content_type="text/plain")
            
            app = web.Application()
            app.router.add_get('/health', health_check)
            app.router.add_get('/metrics', metrics)
            
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, '0.0.0.0', int(os.getenv("METRICS_PORT", "8080")))
            
            if docker_mode:
                # In Docker mode, run the health server and keep the process alive
                await site.start()
                logger.info("health_server_started", port=os.getenv("METRICS_PORT", "8080"))
                logger.info("docker_mode_active", message="Server running in Docker mode, waiting for connections...")
                
                # Keep the process running
                try:
                    while True:
                        await asyncio.sleep(3600)  # Sleep for an hour
                except KeyboardInterrupt:
                    logger.info("server_shutdown", message="Shutting down server...")
                return
            else:
                # In MCP mode, start health server in background
                asyncio.create_task(site.start())
                logger.info("health_server_started", port=os.getenv("METRICS_PORT", "8080"))
        except ImportError:
            logger.warning("aiohttp_not_installed", message="Health check server disabled")
        except Exception as e:
            logger.warning("health_server_failed", error=str(e))
    
    # Run MCP server (only if not in Docker mode)
    if not docker_mode:
        try:
            async with stdio_server() as (read_stream, write_stream):
                logger.info("mcp_server_started", name="congressional-data-mcp")
                init_options = InitializationOptions()
                await server.run(read_stream, write_stream, init_options)
        except Exception as e:
            logger.error("mcp_server_error", error=str(e))
            raise

if __name__ == "__main__":
    asyncio.run(main())
