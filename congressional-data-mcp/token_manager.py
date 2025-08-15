#!/usr/bin/env python3
"""
Token Management System for EnactAI MCP Server
Handles creation, validation, and management of API tokens
"""

import os
import json
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import hmac

# Database path
TOKEN_DB_PATH = os.path.join(os.path.dirname(__file__), "tokens.db")
SECRET_KEY = os.getenv("TOKEN_SECRET_KEY", secrets.token_hex(32))

@dataclass
class Token:
    """Token data structure"""
    id: str
    name: str
    token_hash: str
    created_at: str
    last_used: Optional[str] = None
    expires_at: Optional[str] = None
    permissions: str = "standard"
    active: bool = True
    usage_count: int = 0
    
class TokenManager:
    """Manages API tokens for the MCP server"""
    
    def __init__(self, db_path: str = TOKEN_DB_PATH):
        self.db_path = db_path
        self.secret_key = SECRET_KEY
        self._init_db()
    
    def _init_db(self):
        """Initialize the token database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tokens (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                last_used TEXT,
                expires_at TEXT,
                permissions TEXT DEFAULT 'standard',
                active BOOLEAN DEFAULT 1,
                usage_count INTEGER DEFAULT 0
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS token_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                endpoint TEXT,
                ip_address TEXT,
                status_code INTEGER,
                FOREIGN KEY (token_id) REFERENCES tokens(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _hash_token(self, token: str) -> str:
        """Generate HMAC-SHA256 hash of token"""
        return hmac.new(
            self.secret_key.encode(),
            token.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def create_token(self, name: str, permissions: str = "standard", 
                    expires_days: Optional[int] = None) -> Tuple[str, str]:
        """
        Create a new API token
        
        Args:
            name: Descriptive name for the token
            permissions: Permission level (read_only, standard, admin)
            expires_days: Days until expiration (None = never expires)
        
        Returns:
            Tuple of (token_id, actual_token)
        """
        token_id = secrets.token_hex(8)
        token = f"enact_{secrets.token_urlsafe(32)}"
        token_hash = self._hash_token(token)
        
        created_at = datetime.now(timezone.utc).isoformat()
        expires_at = None
        if expires_days:
            expires_at = (datetime.now(timezone.utc) + timedelta(days=expires_days)).isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO tokens (id, name, token_hash, created_at, expires_at, permissions)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (token_id, name, token_hash, created_at, expires_at, permissions))
        
        conn.commit()
        conn.close()
        
        return token_id, token
    
    def validate_token(self, token: str) -> Optional[Dict]:
        """
        Validate a token and return its details if valid
        
        Args:
            token: The token to validate
            
        Returns:
            Token details if valid, None otherwise
        """
        token_hash = self._hash_token(token)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, created_at, last_used, expires_at, permissions, active, usage_count
            FROM tokens
            WHERE token_hash = ? AND active = 1
        """, (token_hash,))
        
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        token_data = {
            'id': row[0],
            'name': row[1],
            'created_at': row[2],
            'last_used': row[3],
            'expires_at': row[4],
            'permissions': row[5],
            'active': row[6],
            'usage_count': row[7]
        }
        
        # Check expiration
        if token_data['expires_at']:
            expires = datetime.fromisoformat(token_data['expires_at'])
            if datetime.now(timezone.utc) > expires:
                conn.close()
                return None
        
        # Update last used and usage count
        cursor.execute("""
            UPDATE tokens 
            SET last_used = ?, usage_count = usage_count + 1
            WHERE id = ?
        """, (datetime.now(timezone.utc).isoformat(), token_data['id']))
        
        conn.commit()
        conn.close()
        
        return token_data
    
    def record_usage(self, token_id: str, endpoint: str, 
                    ip_address: str = None, status_code: int = 200):
        """Record token usage for analytics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO token_usage (token_id, timestamp, endpoint, ip_address, status_code)
            VALUES (?, ?, ?, ?, ?)
        """, (token_id, datetime.now(timezone.utc).isoformat(), endpoint, ip_address, status_code))
        
        conn.commit()
        conn.close()
    
    def revoke_token(self, token_id: str) -> bool:
        """Revoke a token by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE tokens SET active = 0 WHERE id = ?
        """, (token_id,))
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return affected > 0
    
    def list_tokens(self, active_only: bool = True) -> List[Dict]:
        """List all tokens"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM tokens"
        if active_only:
            query += " WHERE active = 1"
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        
        tokens = []
        for row in rows:
            token_dict = dict(zip(columns, row))
            # Don't expose the hash
            token_dict.pop('token_hash', None)
            tokens.append(token_dict)
        
        conn.close()
        return tokens
    
    def get_token_stats(self, token_id: str, days: int = 7) -> Dict:
        """Get usage statistics for a token"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        # Get usage count
        cursor.execute("""
            SELECT COUNT(*), COUNT(DISTINCT endpoint), COUNT(DISTINCT ip_address)
            FROM token_usage
            WHERE token_id = ? AND timestamp > ?
        """, (token_id, since))
        
        total_requests, unique_endpoints, unique_ips = cursor.fetchone()
        
        # Get endpoint breakdown
        cursor.execute("""
            SELECT endpoint, COUNT(*) as count
            FROM token_usage
            WHERE token_id = ? AND timestamp > ?
            GROUP BY endpoint
            ORDER BY count DESC
            LIMIT 10
        """, (token_id, since))
        
        endpoint_stats = cursor.fetchall()
        
        conn.close()
        
        return {
            'token_id': token_id,
            'period_days': days,
            'total_requests': total_requests,
            'unique_endpoints': unique_endpoints,
            'unique_ips': unique_ips,
            'top_endpoints': [{'endpoint': e[0], 'count': e[1]} for e in endpoint_stats]
        }
    
    def cleanup_expired(self) -> int:
        """Remove expired tokens"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute("""
            UPDATE tokens 
            SET active = 0 
            WHERE expires_at IS NOT NULL AND expires_at < ? AND active = 1
        """, (now,))
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return affected

# CLI functionality
if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Token Management CLI")
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Create token
    create_parser = subparsers.add_parser('create', help='Create a new token')
    create_parser.add_argument('name', help='Token name/description')
    create_parser.add_argument('--permissions', default='standard', 
                              choices=['read_only', 'standard', 'admin'])
    create_parser.add_argument('--expires-days', type=int, help='Days until expiration')
    
    # List tokens
    list_parser = subparsers.add_parser('list', help='List all tokens')
    list_parser.add_argument('--all', action='store_true', help='Include inactive tokens')
    
    # Revoke token
    revoke_parser = subparsers.add_parser('revoke', help='Revoke a token')
    revoke_parser.add_argument('token_id', help='Token ID to revoke')
    
    # Stats
    stats_parser = subparsers.add_parser('stats', help='Get token statistics')
    stats_parser.add_argument('token_id', help='Token ID')
    stats_parser.add_argument('--days', type=int, default=7, help='Days to analyze')
    
    # Cleanup
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up expired tokens')
    
    args = parser.parse_args()
    
    manager = TokenManager()
    
    if args.command == 'create':
        token_id, token = manager.create_token(
            args.name, 
            args.permissions,
            args.expires_days
        )
        print(f"\n✅ Token created successfully!")
        print(f"ID: {token_id}")
        print(f"Name: {args.name}")
        print(f"Permissions: {args.permissions}")
        print(f"Token: {token}")
        print(f"\n⚠️  Save this token securely - it cannot be retrieved again!")
        
    elif args.command == 'list':
        tokens = manager.list_tokens(active_only=not args.all)
        if not tokens:
            print("No tokens found")
        else:
            print(f"\n{'ID':<12} {'Name':<30} {'Permissions':<12} {'Created':<20} {'Used':<8}")
            print("-" * 90)
            for token in tokens:
                created = token['created_at'][:10]
                used = str(token.get('usage_count', 0))
                print(f"{token['id']:<12} {token['name']:<30} {token['permissions']:<12} {created:<20} {used:<8}")
    
    elif args.command == 'revoke':
        if manager.revoke_token(args.token_id):
            print(f"✅ Token {args.token_id} revoked successfully")
        else:
            print(f"❌ Token {args.token_id} not found")
    
    elif args.command == 'stats':
        stats = manager.get_token_stats(args.token_id, args.days)
        print(f"\n📊 Token Statistics (last {args.days} days)")
        print(f"Token ID: {stats['token_id']}")
        print(f"Total Requests: {stats['total_requests']}")
        print(f"Unique Endpoints: {stats['unique_endpoints']}")
        print(f"Unique IPs: {stats['unique_ips']}")
        if stats['top_endpoints']:
            print("\nTop Endpoints:")
            for ep in stats['top_endpoints']:
                print(f"  {ep['endpoint']}: {ep['count']} requests")
    
    elif args.command == 'cleanup':
        removed = manager.cleanup_expired()
        print(f"✅ Cleaned up {removed} expired tokens")
    
    else:
        parser.print_help()