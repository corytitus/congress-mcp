# Congressional MCP Server - Project Status

**Last Updated**: January 16, 2025  
**Version**: 2.0.0 (Stateless Architecture)  
**Status**: ✅ Production Ready

## 🎯 Current State

### Servers Available
1. **`enactai-data-stateless`** - Primary production server with stateless authentication
2. **`enactai-data`** - Enhanced local development server

### Features Implemented
- ✅ **Stateless Authentication** - Token-based authentication that works with MCP protocol
- ✅ **20+ Tools** - Comprehensive Congressional data access
- ✅ **Document Storage** - SQLite-based document management system
- ✅ **Related Bills API** - Find related and similar legislation
- ✅ **Dynamic Congress Detection** - Automatically uses current Congress (119th)
- ✅ **Comprehensive Caching** - 5-minute cache for API responses
- ✅ **Cloud Ready** - FastAPI server for remote deployment

## 📚 Document Library

**21 Congressional Documents** (12.9 MB total)

### Key References
- House Rules and Manual (119th Congress) - 3.3 MB
- Senate Manual (118th Congress) - 2.0 MB  
- House Practice Guide - 3.1 MB
- Constitution of the United States - 147 KB
- How Our Laws Are Made - 355 KB

### Technical Documentation
- 6 XML User Guides
- 2 XML Schemas
- 2 API Documentation files
- 2 Public Meeting Presentations
- 1 Sample Bill Status XML

See `DOCUMENT_LIBRARY.md` for complete listing with document IDs.

## 🛠️ Recent Changes (January 16, 2025)

### Major Updates
1. **Removed Deprecated Components**
   - Deleted old session-based authentication server
   - Removed legacy server.py and simple servers
   - Cleaned up old documentation and scripts
   - Total: 18 deprecated files removed

2. **Added New Features**
   - Related bills API endpoint
   - Document storage system
   - Document upload tools
   - Import scripts for supporting documentation

3. **Documentation Updates**
   - Created API_REFERENCE.md
   - Created USAGE_EXAMPLES.md
   - Created DOCUMENT_LIBRARY.md
   - Updated README.md and CLAUDE.md

4. **Bug Fixes**
   - Fixed datetime deprecation warnings
   - Fixed SQL syntax errors in document store
   - Fixed list_documents tool in enhanced server
   - Removed broken enactai-data-auth from Claude config

## 🔧 Configuration

### Environment Variables Required
```bash
CONGRESS_GOV_API_KEY=your_key_here
GOVINFO_API_KEY=your_key_here
TOKEN_SECRET_KEY=your_secret_key
REQUIRE_AUTH=true  # Set to false for development
```

### Claude Desktop Config
```json
{
  "mcpServers": {
    "enactai-data": {
      "command": "/path/to/run_enactai.sh"
    },
    "enactai-data-stateless": {
      "command": "/path/to/run_stateless.sh"
    }
  }
}
```

## 📊 Available Tools (20+)

### Legislative Data
- `search_bills` - Search Congressional bills
- `get_bill` - Get detailed bill information
- `get_related_bills` - Find related legislation
- `get_member` - Member information
- `search_members` - Search for members
- `get_votes` - Recent voting records
- `get_committee` - Committee information
- `search_amendments` - Search amendments

### Document Management
- `store_document` - Store documents
- `search_documents` - Search stored documents
- `get_document` - Retrieve documents
- `list_documents` - List all documents

### Educational
- `get_current_congress` - Current Congress info
- `get_congress_overview` - How Congress works
- `get_legislative_process` - How bills become laws

### GovInfo
- `search_govinfo` - Search GPO documents
- `get_public_law` - Public law information
- `get_congressional_record` - Congressional Record

## 🚀 Quick Start

### 1. Local Development
```bash
# Set up environment
export CONGRESS_GOV_API_KEY=your_key
export GOVINFO_API_KEY=your_key

# Run enhanced server
./run_enactai.sh
```

### 2. Production (Stateless)
```bash
# Run stateless server
./run_stateless.sh

# In Claude Desktop:
authenticate(token="your_token")
search_bills(query="climate change")
```

### 3. Upload Documents
```bash
# Upload a document
python3 upload_document.py upload document.pdf \
  --title "Title" --category "rules"

# Import supporting docs
python3 import_supporting_docs.py import

# List documents
python3 upload_document.py list
```

## 📁 Project Structure

```
congressional-data-mcp/
├── Core Servers
│   ├── enactai_server_stateless.py    # Primary production
│   ├── enactai_server_enhanced.py     # Local development
│   └── enactai_server_remote.py       # Cloud deployment
├── Document System
│   ├── document_store.py              # Storage backend
│   ├── upload_document.py             # Upload CLI
│   ├── import_supporting_docs.py      # Import script
│   └── documents.db                   # SQLite database
├── Authentication
│   ├── token_manager.py               # Token management
│   └── tokens.db                      # Token database
├── Documentation
│   ├── README.md                      # Main docs
│   ├── CLAUDE.md                      # Claude guidance
│   ├── DOCUMENT_LIBRARY.md           # Document listing
│   ├── PROJECT_STATUS.md             # This file
│   └── docs/
│       ├── API_REFERENCE.md          # API docs
│       └── USAGE_EXAMPLES.md         # Examples
└── Scripts
    ├── run_stateless.sh               # Run production
    └── run_enactai.sh                 # Run development
```

## 🐛 Known Issues

1. **Large Document Downloads** - Some GovInfo documents (Constitution Annotated, Congressional Directory) are too large for simple download
2. **CRS Reports** - Direct CRS report URLs require special access
3. **Rate Limiting** - Congress.gov API limited to 1000 requests/hour

## 📈 Next Steps

### Potential Enhancements
- [ ] Add PDF text extraction for better search
- [ ] Implement document versioning
- [ ] Add bulk document export
- [ ] Create document collections/folders
- [ ] Add document sharing capabilities
- [ ] Implement full-text search with ranking
- [ ] Add document annotation features

### Infrastructure
- [ ] Set up automated testing
- [ ] Add GitHub Actions CI/CD
- [ ] Create Docker images for deployment
- [ ] Set up monitoring and alerting
- [ ] Add rate limiting middleware

## 📞 Support

- **GitHub Issues**: https://github.com/corytitus/congress-mcp/issues
- **API Keys**: 
  - Congress.gov: https://api.congress.gov/
  - GovInfo.gov: https://api.govinfo.gov/

## ✅ Validation Checklist

- [x] Stateless authentication working
- [x] All 20+ tools functional
- [x] Document storage operational
- [x] 21 documents loaded
- [x] Claude Desktop integration working
- [x] Related bills API functional
- [x] Current Congress detection working
- [x] All deprecated code removed
- [x] Documentation complete
- [x] Error handling in place