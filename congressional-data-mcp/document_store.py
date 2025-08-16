#!/usr/bin/env python3
"""
Document Storage System for Congressional MCP Server
Stores and manages uploaded documents, PDFs, and text files
"""

import os
import json
import hashlib
import base64
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
import sqlite3

# Document storage directory
STORAGE_DIR = Path(__file__).parent / "document_storage"
STORAGE_DIR.mkdir(exist_ok=True)

# Database for document metadata
METADATA_DB = Path(__file__).parent / "documents.db"

class DocumentStore:
    """Manages document storage and retrieval"""
    
    def __init__(self):
        self.storage_dir = STORAGE_DIR
        self.db_path = METADATA_DB
        self._init_db()
    
    def _init_db(self):
        """Initialize the document metadata database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                title TEXT,
                description TEXT,
                content_type TEXT,
                size INTEGER,
                hash TEXT UNIQUE,
                uploaded_at TEXT,
                tags TEXT,
                category TEXT,
                full_text TEXT,
                metadata TEXT
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON documents(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags ON documents(tags)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_title ON documents(title)")
        
        conn.commit()
        conn.close()
    
    def store_document(self, 
                      content: bytes,
                      filename: str,
                      title: Optional[str] = None,
                      description: Optional[str] = None,
                      category: Optional[str] = None,
                      tags: Optional[List[str]] = None,
                      metadata: Optional[Dict] = None) -> str:
        """
        Store a document and return its ID
        
        Args:
            content: Document content as bytes
            filename: Original filename
            title: Document title
            description: Document description
            category: Category (e.g., 'legislative_process', 'rules', 'guides')
            tags: List of tags for searching
            metadata: Additional metadata
        
        Returns:
            Document ID
        """
        # Generate document ID and hash
        doc_hash = hashlib.sha256(content).hexdigest()
        doc_id = doc_hash[:12]
        
        # Check if document already exists
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM documents WHERE hash = ?", (doc_hash,))
        existing = cursor.fetchone()
        
        if existing:
            conn.close()
            return existing[0]
        
        # Save file to disk
        file_path = self.storage_dir / f"{doc_id}_{filename}"
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # Extract text content if possible
        full_text = self._extract_text(content, filename)
        
        # Store metadata in database
        cursor.execute("""
            INSERT INTO documents (
                id, filename, title, description, content_type,
                size, hash, uploaded_at, tags, category, full_text, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc_id,
            filename,
            title or filename,
            description,
            self._get_content_type(filename),
            len(content),
            doc_hash,
            datetime.now(timezone.utc).isoformat(),
            json.dumps(tags) if tags else None,
            category,
            full_text,
            json.dumps(metadata) if metadata else None
        ))
        
        conn.commit()
        conn.close()
        
        return doc_id
    
    def get_document(self, doc_id: str) -> Optional[Dict]:
        """Get document metadata and content"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM documents WHERE id = ?
        """, (doc_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        columns = ['id', 'filename', 'title', 'description', 'content_type',
                  'size', 'hash', 'uploaded_at', 'tags', 'category', 
                  'full_text', 'metadata']
        
        doc = dict(zip(columns, row))
        
        # Parse JSON fields
        if doc['tags']:
            doc['tags'] = json.loads(doc['tags'])
        if doc['metadata']:
            doc['metadata'] = json.loads(doc['metadata'])
        
        # Get file path
        doc['file_path'] = str(self.storage_dir / f"{doc_id}_{doc['filename']}")
        
        return doc
    
    def get_document_content(self, doc_id: str) -> Optional[bytes]:
        """Get the actual document content"""
        doc = self.get_document(doc_id)
        if not doc:
            return None
        
        file_path = Path(doc['file_path'])
        if file_path.exists():
            with open(file_path, 'rb') as f:
                return f.read()
        return None
    
    def search_documents(self, 
                        query: Optional[str] = None,
                        category: Optional[str] = None,
                        tags: Optional[List[str]] = None) -> List[Dict]:
        """Search for documents"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        where_clauses = []
        params = []
        
        if query:
            where_clauses.append(
                "(title LIKE ? OR description LIKE ? OR full_text LIKE ?)"
            )
            query_param = f"%{query}%"
            params.extend([query_param, query_param, query_param])
        
        if category:
            where_clauses.append("category = ?")
            params.append(category)
        
        if tags:
            for tag in tags:
                where_clauses.append("tags LIKE ?")
                params.append(f"%{tag}%")
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        cursor.execute(f"""
            SELECT id, filename, title, description, category, tags, 
                   size, uploaded_at
            FROM documents
            WHERE {where_sql}
            ORDER BY uploaded_at DESC
        """, params)
        
        results = []
        for row in cursor.fetchall():
            doc = {
                'id': row[0],
                'filename': row[1],
                'title': row[2],
                'description': row[3],
                'category': row[4],
                'tags': json.loads(row[5]) if row[5] else [],
                'size': row[6],
                'uploaded_at': row[7]
            }
            results.append(doc)
        
        conn.close()
        return results
    
    def list_categories(self) -> List[str]:
        """List all document categories"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT category FROM documents 
            WHERE category IS NOT NULL
            ORDER BY category
        """)
        
        categories = [row[0] for row in cursor.fetchall()]
        conn.close()
        return categories
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete a document"""
        doc = self.get_document(doc_id)
        if not doc:
            return False
        
        # Delete file
        file_path = Path(doc['file_path'])
        if file_path.exists():
            file_path.unlink()
        
        # Delete from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()
        conn.close()
        
        return True
    
    def _extract_text(self, content: bytes, filename: str) -> Optional[str]:
        """Extract text from document"""
        # For now, just handle text files
        # You could add PDF extraction with PyPDF2 or pdfplumber
        if filename.endswith('.txt'):
            try:
                return content.decode('utf-8')
            except:
                return None
        elif filename.endswith('.json'):
            try:
                data = json.loads(content.decode('utf-8'))
                return json.dumps(data, indent=2)
            except:
                return None
        # Add PDF extraction here if needed
        return None
    
    def _get_content_type(self, filename: str) -> str:
        """Get content type from filename"""
        ext = Path(filename).suffix.lower()
        content_types = {
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            '.json': 'application/json',
            '.html': 'text/html',
            '.md': 'text/markdown',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }
        return content_types.get(ext, 'application/octet-stream')

# Pre-loaded Congressional knowledge documents
DEFAULT_DOCUMENTS = {
    "legislative_process": {
        "title": "How a Bill Becomes a Law",
        "category": "legislative_process",
        "tags": ["legislation", "process", "education"],
        "content": """
HOW A BILL BECOMES A LAW

The Legislative Process in the United States Congress

1. INTRODUCTION
- Only a member of Congress can introduce a bill
- Bills can originate in either chamber (except revenue bills - House only)
- Bills are designated HR (House) or S (Senate) plus a number

2. COMMITTEE ACTION
- Bills are referred to appropriate committees based on subject matter
- Committees may hold hearings to gather information
- Committee marks up (amends) the bill
- Committee votes to report the bill, table it, or take no action

3. FLOOR ACTION
- Reported bills are placed on calendar
- Leadership schedules floor consideration
- Chamber debates the bill
- Amendments may be offered
- Chamber votes on final passage

4. SECOND CHAMBER
- Process repeats in the other chamber
- If passed without changes, goes to President
- If passed with changes, differences must be resolved

5. CONFERENCE COMMITTEE
- Members from both chambers negotiate differences
- Compromise version created
- Both chambers must pass identical version

6. PRESIDENTIAL ACTION
- Sign into law
- Veto (return to Congress)
- Pocket veto (don't sign when Congress adjourns)
- Become law without signature (after 10 days)

7. VETO OVERRIDE
- Requires 2/3 vote in both chambers
- If successful, becomes law without President's signature
"""
    },
    
    "committee_system": {
        "title": "Congressional Committee System Guide",
        "category": "organization",
        "tags": ["committees", "organization", "structure"],
        "content": """
THE CONGRESSIONAL COMMITTEE SYSTEM

Committees: The Workhorses of Congress

TYPES OF COMMITTEES:

1. STANDING COMMITTEES
- Permanent panels with specific jurisdictions
- Consider bills and issues
- Conduct oversight of agencies
- Examples: Ways and Means, Armed Services, Judiciary

2. SELECT/SPECIAL COMMITTEES
- Created for specific purpose
- Usually temporary
- Often investigative
- Example: Select Committee on January 6th

3. JOINT COMMITTEES
- Include members from both chambers
- Usually permanent
- Study and report on specific topics
- Example: Joint Committee on Taxation

4. CONFERENCE COMMITTEES
- Temporary
- Resolve differences between House and Senate bills
- Members appointed by leadership

COMMITTEE POWERS:
- Legislative: Draft and amend bills
- Oversight: Monitor executive branch
- Investigative: Subpoena witnesses and documents
- Budget: Authorize spending

COMMITTEE LEADERSHIP:
- Chair (majority party): Sets agenda, calls meetings
- Ranking Member (minority party): Leads opposition
- Subcommittee chairs: Specialized leadership

COMMITTEE PROCESS:
1. Referral: Bills sent to committee
2. Hearings: Gather information
3. Markup: Amend the bill
4. Report: Send to full chamber
5. Conference: Resolve differences
"""
    },
    
    "parliamentary_rules": {
        "title": "Parliamentary Procedures and Rules",
        "category": "procedures",
        "tags": ["rules", "procedures", "parliamentary"],
        "content": """
CONGRESSIONAL PARLIAMENTARY PROCEDURES

HOUSE RULES:
- Debate time strictly limited
- Rules Committee sets terms for each bill
- Amendments must be germane
- Speaker maintains order

Special House Procedures:
- Suspension of rules (2/3 vote, 40 min debate)
- Discharge petition (218 signatures to force bill from committee)
- Motion to recommit (last chance to amend)
- Previous question (end debate)

SENATE RULES:
- Unlimited debate (unless cloture invoked)
- Non-germane amendments usually allowed
- Individual senators have significant power
- Presiding officer has limited power

Special Senate Procedures:
- Filibuster (extended debate to block action)
- Cloture (60 votes to end debate)
- Holds (signal objection to proceeding)
- Unanimous consent (agreements for proceedings)
- Blue slip (home-state senator approval for judges)

VOTING METHODS:
1. Voice Vote: Shouted ayes and noes
2. Division: Members stand to be counted
3. Recorded/Roll Call: Individual positions recorded
4. Unanimous Consent: No objections

MOTIONS:
- Motion to table (kill without direct vote)
- Motion to reconsider (bring back for another vote)
- Motion to adjourn (end session)
- Point of order (question about rules)
"""
    }
}

def load_default_documents():
    """Load default Congressional knowledge documents"""
    store = DocumentStore()
    
    for doc_key, doc_info in DEFAULT_DOCUMENTS.items():
        content = doc_info.pop('content').encode('utf-8')
        filename = f"{doc_key}.txt"
        
        doc_id = store.store_document(
            content=content,
            filename=filename,
            **doc_info
        )
        print(f"Loaded document: {doc_info['title']} (ID: {doc_id})")
    
    return store

if __name__ == "__main__":
    # Test the document store
    store = load_default_documents()
    
    # Search for documents
    print("\nSearching for 'committee' documents:")
    results = store.search_documents(query="committee")
    for doc in results:
        print(f"  - {doc['title']} ({doc['category']})")
    
    print("\nAll categories:")
    for category in store.list_categories():
        print(f"  - {category}")