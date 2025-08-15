"""
Token Management Models and Database Schema
Defines the data models and database structure for secure token management
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import os


class TokenPermission(Enum):
    """Token permission levels."""
    READ_ONLY = "read_only"
    STANDARD = "standard"
    ADMIN = "admin"


@dataclass
class TokenMetadata:
    """Token metadata structure."""
    name: str
    description: str = ""
    permissions: TokenPermission = TokenPermission.STANDARD
    rate_limit: int = 1000  # requests per hour
    allowed_tools: Optional[List[str]] = None  # None means all tools
    ip_whitelist: Optional[List[str]] = None  # None means all IPs
    expires_at: Optional[datetime] = None
    

@dataclass
class Token:
    """Token data structure."""
    id: str
    hashed_token: str
    metadata: TokenMetadata
    created_at: datetime
    last_used_at: Optional[datetime] = None
    usage_count: int = 0
    is_active: bool = True
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[str] = None
    revoked_reason: Optional[str] = None


@dataclass
class TokenUsage:
    """Token usage tracking structure."""
    id: str
    token_id: str
    timestamp: datetime
    tool_name: str
    success: bool
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    response_time_ms: Optional[int] = None
    error_message: Optional[str] = None


class TokenDatabase:
    """SQLite database manager for tokens."""
    
    def __init__(self, db_path: str = "tokens.db"):
        """Initialize the token database."""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS tokens (
                    id TEXT PRIMARY KEY,
                    hashed_token TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    permissions TEXT NOT NULL,
                    rate_limit INTEGER DEFAULT 1000,
                    allowed_tools TEXT,  -- JSON array
                    ip_whitelist TEXT,   -- JSON array
                    expires_at TEXT,     -- ISO format datetime
                    created_at TEXT NOT NULL,
                    last_used_at TEXT,
                    usage_count INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    revoked_at TEXT,
                    revoked_by TEXT,
                    revoked_reason TEXT
                );
                
                CREATE TABLE IF NOT EXISTS token_usage (
                    id TEXT PRIMARY KEY,
                    token_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    response_time_ms INTEGER,
                    error_message TEXT,
                    FOREIGN KEY (token_id) REFERENCES tokens (id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_tokens_hashed ON tokens(hashed_token);
                CREATE INDEX IF NOT EXISTS idx_tokens_active ON tokens(is_active);
                CREATE INDEX IF NOT EXISTS idx_usage_token_id ON token_usage(token_id);
                CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON token_usage(timestamp);
            """)
    
    def _serialize_metadata(self, metadata: TokenMetadata) -> Dict[str, Any]:
        """Serialize metadata for database storage."""
        data = {
            'name': metadata.name,
            'description': metadata.description,
            'permissions': metadata.permissions.value,
            'rate_limit': metadata.rate_limit,
            'allowed_tools': json.dumps(metadata.allowed_tools) if metadata.allowed_tools else None,
            'ip_whitelist': json.dumps(metadata.ip_whitelist) if metadata.ip_whitelist else None,
            'expires_at': metadata.expires_at.isoformat() if metadata.expires_at else None
        }
        return data
    
    def _deserialize_metadata(self, row: Dict[str, Any]) -> TokenMetadata:
        """Deserialize metadata from database row."""
        return TokenMetadata(
            name=row['name'],
            description=row['description'] or "",
            permissions=TokenPermission(row['permissions']),
            rate_limit=row['rate_limit'],
            allowed_tools=json.loads(row['allowed_tools']) if row['allowed_tools'] else None,
            ip_whitelist=json.loads(row['ip_whitelist']) if row['ip_whitelist'] else None,
            expires_at=datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None
        )
    
    def create_token(self, token: Token) -> bool:
        """Create a new token in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                metadata_dict = self._serialize_metadata(token.metadata)
                
                conn.execute("""
                    INSERT INTO tokens (
                        id, hashed_token, name, description, permissions, rate_limit,
                        allowed_tools, ip_whitelist, expires_at, created_at, last_used_at,
                        usage_count, is_active, revoked_at, revoked_by, revoked_reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    token.id,
                    token.hashed_token,
                    metadata_dict['name'],
                    metadata_dict['description'],
                    metadata_dict['permissions'],
                    metadata_dict['rate_limit'],
                    metadata_dict['allowed_tools'],
                    metadata_dict['ip_whitelist'],
                    metadata_dict['expires_at'],
                    token.created_at.isoformat(),
                    token.last_used_at.isoformat() if token.last_used_at else None,
                    token.usage_count,
                    token.is_active,
                    token.revoked_at.isoformat() if token.revoked_at else None,
                    token.revoked_by,
                    token.revoked_reason
                ))
                return True
        except Exception as e:
            print(f"Error creating token: {e}")
            return False
    
    def get_token_by_hash(self, hashed_token: str) -> Optional[Token]:
        """Retrieve token by hashed value."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM tokens WHERE hashed_token = ? AND is_active = 1",
                    (hashed_token,)
                )
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                row_dict = dict(row)
                metadata = self._deserialize_metadata(row_dict)
                
                return Token(
                    id=row_dict['id'],
                    hashed_token=row_dict['hashed_token'],
                    metadata=metadata,
                    created_at=datetime.fromisoformat(row_dict['created_at']),
                    last_used_at=datetime.fromisoformat(row_dict['last_used_at']) if row_dict['last_used_at'] else None,
                    usage_count=row_dict['usage_count'],
                    is_active=bool(row_dict['is_active']),
                    revoked_at=datetime.fromisoformat(row_dict['revoked_at']) if row_dict['revoked_at'] else None,
                    revoked_by=row_dict['revoked_by'],
                    revoked_reason=row_dict['revoked_reason']
                )
        except Exception as e:
            print(f"Error retrieving token: {e}")
            return None
    
    def get_token_by_id(self, token_id: str) -> Optional[Token]:
        """Retrieve token by ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM tokens WHERE id = ?", (token_id,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                row_dict = dict(row)
                metadata = self._deserialize_metadata(row_dict)
                
                return Token(
                    id=row_dict['id'],
                    hashed_token=row_dict['hashed_token'],
                    metadata=metadata,
                    created_at=datetime.fromisoformat(row_dict['created_at']),
                    last_used_at=datetime.fromisoformat(row_dict['last_used_at']) if row_dict['last_used_at'] else None,
                    usage_count=row_dict['usage_count'],
                    is_active=bool(row_dict['is_active']),
                    revoked_at=datetime.fromisoformat(row_dict['revoked_at']) if row_dict['revoked_at'] else None,
                    revoked_by=row_dict['revoked_by'],
                    revoked_reason=row_dict['revoked_reason']
                )
        except Exception as e:
            print(f"Error retrieving token by ID: {e}")
            return None
    
    def list_tokens(self, include_inactive: bool = False) -> List[Token]:
        """List all tokens."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                query = "SELECT * FROM tokens"
                if not include_inactive:
                    query += " WHERE is_active = 1"
                query += " ORDER BY created_at DESC"
                
                cursor = conn.execute(query)
                rows = cursor.fetchall()
                
                tokens = []
                for row in rows:
                    row_dict = dict(row)
                    metadata = self._deserialize_metadata(row_dict)
                    
                    token = Token(
                        id=row_dict['id'],
                        hashed_token=row_dict['hashed_token'],
                        metadata=metadata,
                        created_at=datetime.fromisoformat(row_dict['created_at']),
                        last_used_at=datetime.fromisoformat(row_dict['last_used_at']) if row_dict['last_used_at'] else None,
                        usage_count=row_dict['usage_count'],
                        is_active=bool(row_dict['is_active']),
                        revoked_at=datetime.fromisoformat(row_dict['revoked_at']) if row_dict['revoked_at'] else None,
                        revoked_by=row_dict['revoked_by'],
                        revoked_reason=row_dict['revoked_reason']
                    )
                    tokens.append(token)
                
                return tokens
        except Exception as e:
            print(f"Error listing tokens: {e}")
            return []
    
    def update_token_usage(self, token_id: str, last_used_at: datetime, increment_count: bool = True) -> bool:
        """Update token usage information."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if increment_count:
                    conn.execute("""
                        UPDATE tokens 
                        SET last_used_at = ?, usage_count = usage_count + 1 
                        WHERE id = ?
                    """, (last_used_at.isoformat(), token_id))
                else:
                    conn.execute("""
                        UPDATE tokens 
                        SET last_used_at = ? 
                        WHERE id = ?
                    """, (last_used_at.isoformat(), token_id))
                return True
        except Exception as e:
            print(f"Error updating token usage: {e}")
            return False
    
    def revoke_token(self, token_id: str, revoked_by: str, reason: str = "Manual revocation") -> bool:
        """Revoke a token."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE tokens 
                    SET is_active = 0, revoked_at = ?, revoked_by = ?, revoked_reason = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), revoked_by, reason, token_id))
                return True
        except Exception as e:
            print(f"Error revoking token: {e}")
            return False
    
    def reactivate_token(self, token_id: str) -> bool:
        """Reactivate a revoked token."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE tokens 
                    SET is_active = 1, revoked_at = NULL, revoked_by = NULL, revoked_reason = NULL
                    WHERE id = ?
                """, (token_id,))
                return True
        except Exception as e:
            print(f"Error reactivating token: {e}")
            return False
    
    def log_usage(self, usage: TokenUsage) -> bool:
        """Log token usage."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO token_usage (
                        id, token_id, timestamp, tool_name, success, 
                        ip_address, user_agent, response_time_ms, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    usage.id,
                    usage.token_id,
                    usage.timestamp.isoformat(),
                    usage.tool_name,
                    usage.success,
                    usage.ip_address,
                    usage.user_agent,
                    usage.response_time_ms,
                    usage.error_message
                ))
                return True
        except Exception as e:
            print(f"Error logging usage: {e}")
            return False
    
    def get_usage_stats(self, token_id: str, hours: int = 24) -> Dict[str, Any]:
        """Get usage statistics for a token."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                since = datetime.now() - timedelta(hours=hours)
                
                # Total requests in time period
                cursor = conn.execute("""
                    SELECT COUNT(*) as total_requests,
                           SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_requests,
                           AVG(response_time_ms) as avg_response_time
                    FROM token_usage 
                    WHERE token_id = ? AND timestamp >= ?
                """, (token_id, since.isoformat()))
                
                stats = dict(cursor.fetchone())
                
                # Requests by tool
                cursor = conn.execute("""
                    SELECT tool_name, COUNT(*) as count
                    FROM token_usage 
                    WHERE token_id = ? AND timestamp >= ?
                    GROUP BY tool_name
                    ORDER BY count DESC
                """, (token_id, since.isoformat()))
                
                tools_usage = [dict(row) for row in cursor.fetchall()]
                
                return {
                    "period_hours": hours,
                    "total_requests": stats["total_requests"] or 0,
                    "successful_requests": stats["successful_requests"] or 0,
                    "error_rate": (stats["total_requests"] - (stats["successful_requests"] or 0)) / max(stats["total_requests"] or 1, 1),
                    "avg_response_time_ms": stats["avg_response_time"] or 0,
                    "tools_usage": tools_usage
                }
        except Exception as e:
            print(f"Error getting usage stats: {e}")
            return {"error": str(e)}
    
    def cleanup_old_usage(self, days: int = 30) -> bool:
        """Clean up old usage records."""
        try:
            cutoff = datetime.now() - timedelta(days=days)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM token_usage WHERE timestamp < ?
                """, (cutoff.isoformat(),))
                deleted_count = cursor.rowcount
                print(f"Cleaned up {deleted_count} old usage records")
                return True
        except Exception as e:
            print(f"Error cleaning up usage records: {e}")
            return False