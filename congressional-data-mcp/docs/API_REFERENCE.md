# Congressional MCP Server API Reference

## Overview

The Congressional MCP Server provides access to authoritative legislative data from Congress.gov and GovInfo.gov APIs through the Model Context Protocol (MCP). This reference documents all available tools, their parameters, and example usage.

## Authentication

### Stateless Authentication (Recommended)

The server uses token-based authentication where tokens are included in every request.

```json
{
  "tool": "authenticate",
  "arguments": {
    "token": "your_api_token_here"
  }
}
```

### Token Permissions

- **admin**: Full access to all tools
- **standard**: Access to all read and write tools
- **read_only**: Access to read-only tools only

## Available Tools

### 1. authenticate

Validate your API token for subsequent requests.

**Parameters:**
- `token` (string, required): Your API token

**Response:**
```json
{
  "status": "authenticated",
  "token_id": "token_abc123",
  "name": "User Name",
  "permissions": "admin",
  "message": "Token validated! Include this token in all subsequent tool calls."
}
```

### 2. search_bills

Search for congressional bills with advanced filtering.

**Parameters:**
- `token` (string): Your API token (required if auth enabled)
- `query` (string): Search query
- `congress` (integer): Congress number (defaults to current Congress)
- `chamber` (string): "house", "senate", or "both"
- `limit` (integer): Maximum results (default 20)

**Example:**
```json
{
  "tool": "search_bills",
  "arguments": {
    "token": "your_token",
    "query": "climate change",
    "congress": 119,
    "chamber": "both",
    "limit": 10
  }
}
```

### 3. get_bill

Get comprehensive information about a specific bill.

**Parameters:**
- `token` (string): Your API token
- `congress` (integer, required): Congress number
- `bill_type` (string, required): Bill type (hr, s, hjres, sjres, hres, sres, hconres, sconres)
- `bill_number` (integer, required): Bill number

**Example:**
```json
{
  "tool": "get_bill",
  "arguments": {
    "token": "your_token",
    "congress": 119,
    "bill_type": "hr",
    "bill_number": 1
  }
}
```

### 4. get_related_bills

Get bills related to a specific bill (similar bills, procedurally-related bills, etc.)

**Parameters:**
- `token` (string): Your API token
- `congress` (integer, required): Congress number
- `bill_type` (string, required): Bill type
- `bill_number` (integer, required): Bill number
- `limit` (integer): Maximum results (default 20)

**Example:**
```json
{
  "tool": "get_related_bills",
  "arguments": {
    "token": "your_token",
    "congress": 117,
    "bill_type": "hr",
    "bill_number": 3076,
    "limit": 10
  }
}
```

**Response Structure:**
```json
{
  "originalBill": {
    "congress": 117,
    "type": "HR",
    "number": 3076,
    "identifier": "HR 3076 (117th Congress)"
  },
  "relatedBills": [
    {
      "congress": 117,
      "type": "S",
      "number": 1720,
      "title": "Postal Service Reform Act of 2021",
      "latestAction": {
        "actionDate": "2021-05-19",
        "text": "Read twice and referred to the Committee..."
      },
      "relationships": [
        {
          "type": "Related bill",
          "identifiedBy": "CRS"
        }
      ]
    }
  ],
  "count": 4,
  "source": "Source: Library of Congress (congress.gov) - Related bills for HR 3076 (117th Congress)"
}
```

### 5. get_member

Get detailed information about a member of Congress.

**Parameters:**
- `token` (string): Your API token
- `bioguide_id` (string, required): Member's bioguide ID

**Example:**
```json
{
  "tool": "get_member",
  "arguments": {
    "token": "your_token",
    "bioguide_id": "P000197"
  }
}
```

### 6. search_members

Search for members of Congress by various criteria.

**Parameters:**
- `token` (string): Your API token
- `state` (string): Two-letter state code
- `party` (string): Party affiliation (D, R, I)
- `chamber` (string): "house" or "senate"
- `limit` (integer): Maximum results (default 20)

### 7. get_votes

Get recent votes from House or Senate.

**Parameters:**
- `token` (string): Your API token
- `chamber` (string, required): "house" or "senate"
- `limit` (integer): Number of votes to retrieve (default 10)

### 8. get_committee

Get information about a congressional committee.

**Parameters:**
- `token` (string): Your API token
- `chamber` (string, required): "house" or "senate"
- `committee_code` (string, required): Committee code

### 9. search_amendments

Search for amendments to bills.

**Parameters:**
- `token` (string): Your API token
- `congress` (integer): Congress number
- `limit` (integer): Maximum results (default 20)

### 10. get_current_congress

Get information about the current Congress session.

**Parameters:**
- `token` (string): Your API token

**Response:**
```json
{
  "current_congress": {
    "number": 119,
    "name": "119th Congress",
    "start_year": 2025,
    "end_year": 2026,
    "sessions": [...],
    "type": "CONGRESS"
  },
  "note": "Congress sessions run for 2 years, with new Congress every odd year",
  "source": "Source: Library of Congress (congress.gov) - Congress 119 Information"
}
```

## Document Storage Tools

### 11. store_document

Store a document in the knowledge base.

**Parameters:**
- `token` (string): Your API token
- `content` (string, required): Document content (text or base64-encoded binary)
- `filename` (string, required): Original filename
- `title` (string): Document title
- `description` (string): Document description
- `category` (string): Category (e.g., 'legislative_process', 'rules', 'guides')
- `tags` (array): List of tags for searching
- `is_binary` (boolean): Whether content is base64-encoded binary

**Example:**
```json
{
  "tool": "store_document",
  "arguments": {
    "token": "your_token",
    "content": "Content of the document...",
    "filename": "senate_rules.txt",
    "title": "Senate Parliamentary Rules",
    "description": "Complete guide to Senate procedures",
    "category": "rules",
    "tags": ["senate", "procedures", "parliamentary"]
  }
}
```

### 12. search_documents

Search for stored documents.

**Parameters:**
- `token` (string): Your API token
- `query` (string): Search query
- `category` (string): Filter by category
- `tags` (array): Filter by tags

**Example:**
```json
{
  "tool": "search_documents",
  "arguments": {
    "token": "your_token",
    "query": "filibuster",
    "category": "procedures"
  }
}
```

### 13. get_document

Retrieve a specific document.

**Parameters:**
- `token` (string): Your API token
- `doc_id` (string, required): Document ID
- `include_content` (boolean): Include full content (default false)

### 14. list_documents

List all stored documents.

**Parameters:**
- `token` (string): Your API token
- `category` (string): Filter by category

## Educational Tools

### 15. get_congress_overview

Get educational overview of how Congress works.

**Parameters:**
- `token` (string): Your API token

**Response includes:**
- Structure of Senate and House
- Powers of Congress
- Current and previous Congress information

### 16. get_legislative_process

Learn about the legislative process and how bills become laws.

**Parameters:**
- `token` (string): Your API token

**Response includes:**
- Step-by-step process
- Key terminology
- Procedural information

## GovInfo Tools

### 17. search_govinfo

Search Government Publishing Office documents.

**Parameters:**
- `token` (string): Your API token
- `query` (string, required): Search query
- `collection` (string): Collection to search
- `limit` (integer): Maximum results (default 20)

### 18. get_public_law

Get information about a public law.

**Parameters:**
- `token` (string): Your API token
- `congress` (integer, required): Congress number
- `law_number` (integer, required): Law number

### 19. get_congressional_record

Search the Congressional Record.

**Parameters:**
- `token` (string): Your API token
- `date` (string): Date in YYYY-MM-DD format
- `section` (string): Section to search
- `limit` (integer): Maximum results (default 20)

## Response Format

All tools return JSON responses with the following structure:

### Success Response
```json
{
  "results": [...],
  "count": 10,
  "source": "Source: Library of Congress (congress.gov) - [identifier]"
}
```

### Error Response
```json
{
  "error": "Error message",
  "message": "User-friendly error description",
  "tool": "tool_name"
}
```

## Rate Limits

- **Congress.gov API**: 1000 requests/hour
- **GovInfo.gov API**: Varies by endpoint
- **Cache TTL**: 5 minutes for most responses
- **Congress Cache TTL**: 1 day for current Congress information

## Best Practices

1. **Always include your token** in every request after authentication
2. **Use caching** - repeated identical requests within 5 minutes return cached results
3. **Be specific** with search queries to get better results
4. **Use appropriate limits** to avoid overwhelming responses
5. **Check permissions** - ensure your token has the required permissions for the tools you're using

## Example Workflow

```python
# 1. Authenticate
authenticate(token="your_token")

# 2. Search for bills
results = search_bills(query="healthcare", congress=119, limit=5)

# 3. Get details on a specific bill
bill = get_bill(congress=119, bill_type="hr", bill_number=1)

# 4. Find related bills
related = get_related_bills(congress=119, bill_type="hr", bill_number=1)

# 5. Store a document about the bill
doc_id = store_document(
    content="Analysis of HR 1...",
    filename="hr1_analysis.txt",
    title="HR 1 Analysis",
    category="analysis"
)
```

## Error Codes

- **401**: Authentication required or invalid token
- **403**: Permission denied for this tool
- **404**: Resource not found
- **429**: Rate limit exceeded
- **500**: Internal server error

## Support

For API keys and support:
- Congress.gov API: https://api.congress.gov/
- GovInfo.gov API: https://api.govinfo.gov/
- Project Issues: https://github.com/corytitus/congress-mcp/issues