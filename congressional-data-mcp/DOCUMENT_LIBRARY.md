# Congressional Document Library

**Last Updated**: January 16, 2025  
**Total Documents**: 21 documents (12.9 MB)

## 📚 Complete Document Collection

### 📜 Foundational Documents
| Document | ID | Size | Description |
|----------|-----|------|-------------|
| **Constitution of the United States** | `5282c202ccdc` | 147 KB | The Constitution with index, Bill of Rights, and all amendments |

### 📋 Rules & Manuals
| Document | ID | Size | Description |
|----------|-----|------|-------------|
| **House Rules and Manual - 119th Congress** | `c51acd6c0682` | 3.3 MB | Official Rules of the House of Representatives for 2025-2026 |
| **Senate Manual - 118th Congress** | `2d2dc6d93f3b` | 2.0 MB | Standing Rules, Orders, Laws, and Resolutions of the Senate |

### 📖 Procedures & Practice
| Document | ID | Size | Description |
|----------|-----|------|-------------|
| **House Practice Guide** | `03a17d339e7d` | 3.1 MB | Comprehensive guide to House rules, precedents, and procedures |
| **Parliamentary Procedures and Rules** | `e7e86332fca8` | 1.2 KB | Overview of parliamentary procedures |

### 🎓 Legislative Process Education
| Document | ID | Size | Description |
|----------|-----|------|-------------|
| **How Our Laws Are Made - 110th Congress** | `3e894867dfcf` | 355 KB | Official guide explaining the legislative process (House Doc. 49) |
| **How a Bill Becomes a Law** | `35a344dfefed` | 1.3 KB | Educational overview of the legislative process |

### 🏛️ Organization
| Document | ID | Size | Description |
|----------|-----|------|-------------|
| **Congressional Committee System Guide** | `47ede302a974` | 1.2 KB | Overview of committee structure and functions |

### 💻 Technical Documentation

#### API Documentation
| Document | ID | Size | Description |
|----------|-----|------|-------------|
| **Congress.gov API Documentation** | `bce725d0a9e3` | 18 KB | Official API documentation for Congress.gov |
| **Link Service Documentation** | `b8f147a7723d` | 36 KB | Documentation for the Congress.gov link service |

#### XML Guides
| Document | ID | Size | Description |
|----------|-----|------|-------------|
| **Bill Status XML User Guide** | `24527fbffc14` | 252 KB | Complete guide to Bill Status XML format (PDF) |
| **Bill Status XML Guide (Markdown)** | `a10909696b2e` | 38 KB | Markdown version of Bill Status documentation |
| **Bills XML User Guide** | `f173cad9f5eb` | 8 KB | Guide to Bills XML format |
| **Bills Summary XML User Guide** | `0616a451fa87` | 23 KB | Guide to Bills Summary XML format |
| **USLM User Guide** | `f552c6d56b3c` | 1.0 MB | United States Legislative Markup Language guide |
| **USLM 2.1 Review Guide** | `02fddebb4fa2` | 134 KB | Review guide for USLM version 2.1 |

#### Schemas
| Document | ID | Size | Description |
|----------|-----|------|-------------|
| **USLM XML Schema** | `dba603fcb1b4` | 184 KB | XML Schema Definition for USLM format |
| **USLM 2.1.0 XML Schema** | `cd9cc6421a45` | 2 KB | XML Schema for USLM version 2.1.0 |

### 📊 Presentations
| Document | ID | Size | Description |
|----------|-----|------|-------------|
| **Bill Status in Bulk (Dec 2015)** | `2ddf5b4901d7` | 620 KB | Public meeting presentation on bulk data |
| **Bill Status in Bulk (Apr 2016)** | `f05793b7e4c7` | 599 KB | Follow-up presentation on implementation |

### 📝 Sample Documents
| Document | ID | Size | Description |
|----------|-----|------|-------------|
| **Sample Bill Status - HR 2670** | `7f6418f745ed` | 1.1 MB | Complete bill status XML example for HR 2670 (118th Congress) |

## 🔍 Accessing Documents

### Through Claude Desktop (MCP Tools)

```python
# Authenticate first
authenticate(token="your_token")

# List all documents
search_documents()  # Returns all documents

# Search by category
search_documents(category="rules")
search_documents(category="technical_guides")

# Search by content
search_documents(query="filibuster")
search_documents(query="committee")

# Get specific document
get_document(doc_id="c51acd6c0682")  # House Rules Manual
get_document(doc_id="3e894867dfcf")  # How Laws Are Made
```

### Through Command Line

```bash
# List all documents
python3 upload_document.py list

# Search documents
python3 upload_document.py search "senate procedures"
python3 upload_document.py search "xml guide"

# Upload new documents
python3 upload_document.py upload [file.pdf] \
  --title "Document Title" \
  --category "category" \
  --tags "tag1,tag2"

# Import supporting documentation
python3 import_supporting_docs.py import
```

## 📁 Document Categories

- **`foundational_documents`** - Constitution and founding documents
- **`rules`** - House and Senate rules and manuals
- **`procedures`** - Parliamentary procedures and practices
- **`legislative_process`** - How bills become laws
- **`organization`** - Committee structures and member information
- **`technical_guides`** - XML and API documentation
- **`api_documentation`** - API references and guides
- **`schemas`** - XML schemas for validation
- **`presentations`** - Meeting materials and presentations
- **`samples`** - Example bills and documents

## 📂 Storage Locations

- **Database**: `/congressional-data-mcp/documents.db` - Metadata and search index
- **Files**: `/congressional-data-mcp/document_storage/` - Actual document files
- **Supporting Docs**: `/supportingDocumentation/` - Source documentation folder

## 🆕 Recently Added (January 16, 2025)

1. House Rules and Manual - 119th Congress
2. Senate Manual - 118th Congress  
3. House Practice Guide
4. Constitution of the United States
5. How Our Laws Are Made
6. 13 Technical guides and schemas from supporting documentation

## 📈 Quick Stats

- **Total Size**: 12.9 MB
- **Largest Document**: House Rules Manual (3.3 MB)
- **Most Technical Docs**: 6 XML guides
- **Categories**: 10 different categories
- **File Types**: PDF, XML, XSD, Markdown, Text

## 🚀 Usage Examples

### Finding Rules and Procedures
```python
# Get House rules
doc = get_document("c51acd6c0682")

# Search for Senate procedures
results = search_documents(query="senate", category="rules")

# Find filibuster information
results = search_documents(query="filibuster")
```

### Technical Documentation
```python
# Get all XML guides
results = search_documents(category="technical_guides")

# Find API documentation
results = search_documents(query="API")

# Get XML schemas
results = search_documents(category="schemas")
```

### Educational Materials
```python
# Legislative process documents
results = search_documents(category="legislative_process")

# Committee information
results = search_documents(query="committee")
```