# Congressional MCP Server Usage Examples

## Table of Contents
- [Claude Desktop Integration](#claude-desktop-integration)
- [Common Use Cases](#common-use-cases)
- [Python Integration](#python-integration)
- [Remote Server Usage](#remote-server-usage)
- [Document Management](#document-management)
- [Advanced Queries](#advanced-queries)

## Claude Desktop Integration

### Basic Setup and Authentication

1. **Start a conversation with Claude Desktop**
2. **Authenticate with your token:**
```
Use the authenticate tool with token: enact_0Rk5yidWIB36mbmYMO8Fj7PxKPkplcb70TfyQxV9n_g
```

3. **Claude will confirm authentication:**
```
✅ Token validated! You now have admin access to all Congressional data tools.
```

### Example Conversations

#### Finding Recent Climate Legislation
```
User: Search for recent bills about climate change in the current Congress

Claude: I'll search for climate change bills in the 119th Congress.

[Uses search_bills tool]

I found 15 bills related to climate change in the 119th Congress. Here are the top 5:

1. HR 123 - Clean Energy Innovation Act
   Sponsor: Rep. Smith (D-CA)
   Status: In Committee
   
2. S 456 - Climate Resilience and Adaptation Act
   Sponsor: Sen. Johnson (D-NY)
   Status: Passed Senate
   
[... more results ...]
```

#### Tracking a Specific Bill
```
User: Tell me about HR 1 from the 119th Congress and find related bills

Claude: I'll get detailed information about HR 1 and find related bills.

[Uses get_bill and get_related_bills tools]

HR 1 - For the People Act of 2025
Sponsor: Rep. Sarbanes (D-MD)
Introduced: January 3, 2025
Status: In House Judiciary Committee

Summary: This bill addresses voter access, election integrity, and campaign finance...

Related Bills Found (4):
- S 1 (119th) - Identical bill in Senate
- HR 4 (119th) - Related bill addressing voting rights
- HR 2353 (118th) - Previous version from last Congress
```

#### Understanding Committee Assignments
```
User: Who's on the House Ways and Means Committee?

Claude: I'll get the current membership of the House Ways and Means Committee.

[Uses get_committee tool]

House Ways and Means Committee (119th Congress)
Chair: Rep. Richard Neal (D-MA)
Ranking Member: Rep. Jason Smith (R-MO)

Democratic Members (25):
- Rep. Lloyd Doggett (D-TX)
- Rep. Mike Thompson (D-CA)
[... more members ...]
```

## Common Use Cases

### Legislative Research Workflow

```python
# 1. Find bills on a topic
search_bills(query="infrastructure", congress=119, chamber="both")

# 2. Get detailed information on interesting bills
get_bill(congress=119, bill_type="hr", bill_number=2345)

# 3. Find related legislation
get_related_bills(congress=119, bill_type="hr", bill_number=2345)

# 4. Check committee status
get_committee(chamber="house", committee_code="PW00")

# 5. Review recent votes
get_votes(chamber="house", limit=10)
```

### Member Analysis

```python
# Find all senators from a state
search_members(state="CA", chamber="senate")

# Get detailed member profile
get_member(bioguide_id="F000062")

# Check voting record
get_member_votes(bioguide_id="F000062", limit=50)
```

### Historical Research

```python
# Search Congressional Record
get_congressional_record(date="2025-01-15", section="house")

# Find public laws
get_public_law(congress=118, law_number=31)

# Search government documents
search_govinfo(query="budget reconciliation", collection="BILLS")
```

## Python Integration

### Basic Script Example

```python
import asyncio
import httpx
from typing import Dict, Any

async def query_congress_data():
    """Example of using the MCP server from Python"""
    
    # Initialize client
    base_url = "http://localhost:8000"  # For local server
    token = "your_api_token"
    
    async with httpx.AsyncClient() as client:
        # Authenticate
        auth_response = await client.post(
            f"{base_url}/mcp/tool",
            json={
                "tool": "authenticate",
                "arguments": {"token": token}
            }
        )
        print("Authenticated:", auth_response.json())
        
        # Search for bills
        bills_response = await client.post(
            f"{base_url}/mcp/tool",
            json={
                "tool": "search_bills",
                "arguments": {
                    "token": token,
                    "query": "healthcare",
                    "congress": 119,
                    "limit": 5
                }
            }
        )
        
        bills = bills_response.json()
        print(f"Found {bills['count']} bills")
        
        # Get details on first bill
        if bills['results']:
            first_bill = bills['results'][0]
            bill_detail = await client.post(
                f"{base_url}/mcp/tool",
                json={
                    "tool": "get_bill",
                    "arguments": {
                        "token": token,
                        "congress": first_bill['congress'],
                        "bill_type": first_bill['type'].lower(),
                        "bill_number": first_bill['number']
                    }
                }
            )
            print("Bill details:", bill_detail.json())

# Run the example
asyncio.run(query_congress_data())
```

### Batch Processing Example

```python
async def analyze_voting_patterns():
    """Analyze voting patterns across multiple bills"""
    
    # Get recent votes
    votes = await get_votes(chamber="senate", limit=20)
    
    voting_data = []
    for vote in votes['results']:
        # Get detailed vote information
        vote_detail = await get_vote(
            congress=vote['congress'],
            chamber="senate",
            roll_number=vote['rollNumber']
        )
        
        # Analyze party-line votes
        party_breakdown = analyze_party_votes(vote_detail)
        voting_data.append({
            'vote': vote['question'],
            'result': vote['result'],
            'party_unity': party_breakdown
        })
    
    return voting_data
```

## Remote Server Usage

### Using the FastAPI Remote Server

```bash
# Deploy to cloud (e.g., Railway)
railway up

# Get your server URL
SERVER_URL=https://your-app.railway.app

# Test with curl
curl -X POST $SERVER_URL/mcp/tool \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ENACTAI_API_TOKEN" \
  -d '{
    "tool": "search_bills",
    "arguments": {
      "query": "education",
      "congress": 119
    }
  }'
```

### JavaScript/TypeScript Integration

```typescript
async function searchBills(query: string): Promise<any> {
  const response = await fetch('https://your-server.com/mcp/tool', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${process.env.API_TOKEN}`
    },
    body: JSON.stringify({
      tool: 'search_bills',
      arguments: {
        query,
        congress: 119,
        limit: 10
      }
    })
  });
  
  return response.json();
}
```

## Document Management

### Uploading Documents

```python
# Upload a PDF document
with open('senate_rules.pdf', 'rb') as f:
    content = base64.b64encode(f.read()).decode()
    
doc_id = store_document(
    content=content,
    filename="senate_rules.pdf",
    title="Senate Parliamentary Rules 2025",
    description="Complete guide to Senate procedures",
    category="rules",
    tags=["senate", "procedures", "parliamentary"],
    is_binary=True
)
print(f"Document stored with ID: {doc_id}")
```

### Searching Documents

```python
# Search for filibuster information
results = search_documents(
    query="filibuster",
    category="procedures"
)

for doc in results['results']:
    print(f"{doc['title']} - {doc['description']}")
    print(f"Tags: {', '.join(doc['tags'])}")
```

### Bulk Document Upload

```bash
# Using the upload script
python upload_document.py upload senate_rules.pdf \
  --title "Senate Rules" \
  --category "rules" \
  --tags "senate,procedures"

# Upload entire directory
python upload_document.py upload-dir ./documents \
  --category "reference"

# List all documents
python upload_document.py list

# Search documents
python upload_document.py search "committee procedures"
```

## Advanced Queries

### Complex Bill Analysis

```python
async def comprehensive_bill_analysis(congress: int, bill_type: str, number: int):
    """Perform comprehensive analysis of a bill"""
    
    # Get bill details
    bill = await get_bill(congress, bill_type, number)
    
    # Get related bills
    related = await get_related_bills(congress, bill_type, number)
    
    # Get sponsor information
    sponsor_id = bill['bill']['sponsors'][0]['bioguideId']
    sponsor = await get_member(sponsor_id)
    
    # Get committee information
    committees = bill['bill']['committees']
    committee_details = []
    for comm in committees:
        details = await get_committee(
            chamber=comm['chamber'].lower(),
            committee_code=comm['systemCode']
        )
        committee_details.append(details)
    
    # Search for amendments
    amendments = await search_amendments(congress=congress)
    bill_amendments = [a for a in amendments['results'] 
                       if a['billNumber'] == number]
    
    return {
        'bill': bill,
        'related_bills': related,
        'sponsor': sponsor,
        'committees': committee_details,
        'amendments': bill_amendments
    }
```

### Tracking Legislative Progress

```python
def track_bill_progress(congress: int, bill_type: str, number: int):
    """Track a bill's progress through Congress"""
    
    bill = get_bill(congress, bill_type, number)
    
    progress = {
        'introduced': False,
        'committee': False,
        'floor_action': False,
        'passed_originating': False,
        'passed_other': False,
        'conference': False,
        'passed_both': False,
        'president': False,
        'law': False
    }
    
    # Check actions to determine progress
    for action in bill['bill']['actions']:
        action_text = action['text'].lower()
        
        if 'introduced' in action_text:
            progress['introduced'] = True
        elif 'referred to' in action_text and 'committee' in action_text:
            progress['committee'] = True
        elif 'passed' in action_text:
            if bill_type in ['hr', 'hjres', 'hconres', 'hres']:
                if 'house' in action_text:
                    progress['passed_originating'] = True
                elif 'senate' in action_text:
                    progress['passed_other'] = True
            else:
                if 'senate' in action_text:
                    progress['passed_originating'] = True
                elif 'house' in action_text:
                    progress['passed_other'] = True
        elif 'conference' in action_text:
            progress['conference'] = True
        elif 'presented to president' in action_text:
            progress['president'] = True
        elif 'became public law' in action_text:
            progress['law'] = True
    
    return progress
```

### Creating Reports

```python
async def generate_weekly_report():
    """Generate a weekly legislative activity report"""
    
    report = {
        'date': datetime.now().isoformat(),
        'congress': 119,
        'activity': {}
    }
    
    # Get recent bills
    recent_bills = await search_bills(congress=119, limit=50)
    report['activity']['new_bills'] = recent_bills['count']
    
    # Get recent votes
    house_votes = await get_votes(chamber="house", limit=10)
    senate_votes = await get_votes(chamber="senate", limit=10)
    report['activity']['votes'] = {
        'house': len(house_votes['results']),
        'senate': len(senate_votes['results'])
    }
    
    # Get committee activity
    # ... additional analysis ...
    
    # Store report as document
    doc_id = await store_document(
        content=json.dumps(report, indent=2),
        filename=f"weekly_report_{datetime.now().strftime('%Y%m%d')}.json",
        title=f"Weekly Legislative Report - {datetime.now().strftime('%B %d, %Y')}",
        category="reports",
        tags=["weekly", "report", "activity"]
    )
    
    return report
```

## Tips and Best Practices

1. **Use specific queries** - More specific search terms yield better results
2. **Leverage caching** - Repeated queries within 5 minutes use cached data
3. **Batch related requests** - Group related API calls for efficiency
4. **Monitor rate limits** - Stay within API rate limits (1000/hour for Congress.gov)
5. **Store important documents** - Use document storage for frequently referenced materials
6. **Use appropriate tools** - Choose the right tool for your specific need
7. **Handle errors gracefully** - Always include error handling in production code

## Troubleshooting

### Common Issues

**Authentication Failures:**
```python
# Check if token is valid
result = authenticate(token="your_token")
if "error" in result:
    print("Authentication failed:", result["error"])
```

**Rate Limiting:**
```python
# Implement exponential backoff
import time

async def retry_with_backoff(func, *args, max_retries=3):
    for i in range(max_retries):
        try:
            return await func(*args)
        except RateLimitError:
            wait_time = 2 ** i
            print(f"Rate limited, waiting {wait_time} seconds...")
            time.sleep(wait_time)
    raise Exception("Max retries exceeded")
```

**Empty Results:**
```python
# Check multiple congresses if no results
for congress in [119, 118, 117]:
    results = search_bills(query="your_query", congress=congress)
    if results['count'] > 0:
        break
```

## Additional Resources

- [API Reference](./API_REFERENCE.md) - Complete API documentation
- [Deployment Guide](../DEPLOYMENT.md) - Cloud deployment instructions
- [Authentication Guide](../STATELESS_AUTH_GUIDE.md) - Token management
- [GitHub Repository](https://github.com/corytitus/congress-mcp) - Source code and issues