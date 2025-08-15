#!/usr/bin/env python3
"""
Token Management CLI
Command-line interface for managing API tokens
"""

import sys
import argparse
import json
from datetime import datetime
from typing import List, Optional
import os

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from token_manager import TokenManager, get_token_manager
from token_models import TokenPermission
from token_security import mask_token_for_display


class TokenCLI:
    """Command-line interface for token management."""
    
    def __init__(self):
        """Initialize the CLI."""
        self.manager = get_token_manager()
    
    def create_token(self, args):
        """Create a new token."""
        print(f"Creating token '{args.name}'...")
        
        # Parse permissions
        try:
            permissions = TokenPermission(args.permissions)
        except ValueError:
            print(f"Error: Invalid permission level '{args.permissions}'")
            print(f"Valid options: {', '.join([p.value for p in TokenPermission])}")
            return 1
        
        # Parse allowed tools
        allowed_tools = None
        if args.allowed_tools:
            allowed_tools = [tool.strip() for tool in args.allowed_tools.split(',')]
        
        # Parse IP whitelist
        ip_whitelist = None
        if args.ip_whitelist:
            ip_whitelist = [ip.strip() for ip in args.ip_whitelist.split(',')]
        
        # Create the token
        success, message, token = self.manager.create_token(
            name=args.name,
            description=args.description or "",
            permissions=permissions,
            rate_limit=args.rate_limit,
            allowed_tools=allowed_tools,
            ip_whitelist=ip_whitelist,
            expires_in_days=args.expires_in_days
        )
        
        if success:
            print("✓ Token created successfully!")
            print(f"  Name: {args.name}")
            print(f"  Token: {token}")
            print(f"  Permissions: {args.permissions}")
            print(f"  Rate Limit: {args.rate_limit} requests/hour")
            
            if allowed_tools:
                print(f"  Allowed Tools: {', '.join(allowed_tools)}")
            
            if ip_whitelist:
                print(f"  IP Whitelist: {', '.join(ip_whitelist)}")
            
            if args.expires_in_days:
                print(f"  Expires: {args.expires_in_days} days from now")
            
            print("\n⚠️  IMPORTANT: Save this token securely. It cannot be retrieved again!")
            
        else:
            print(f"✗ Error: {message}")
            return 1
        
        return 0
    
    def list_tokens(self, args):
        """List all tokens."""
        tokens = self.manager.list_tokens(include_inactive=args.include_inactive)
        
        if not tokens:
            print("No tokens found.")
            return 0
        
        if 'error' in tokens[0]:
            print(f"Error: {tokens[0]['error']}")
            return 1
        
        # Format output
        if args.format == 'json':
            print(json.dumps(tokens, indent=2))
        else:
            # Table format
            print(f"{'ID':<16} {'Name':<20} {'Permissions':<12} {'Active':<8} {'Usage':<8} {'Created':<12}")
            print("-" * 80)
            
            for token in tokens:
                status = "✓" if token['is_active'] else "✗"
                created = datetime.fromisoformat(token['created_at']).strftime('%Y-%m-%d')
                
                print(f"{token['id'][:16]:<16} {token['name'][:20]:<20} "
                      f"{token['permissions']:<12} {status:<8} {token['usage_count']:<8} {created:<12}")
        
        return 0
    
    def show_token(self, args):
        """Show detailed information about a token."""
        token_info = self.manager.get_token_info(args.identifier)
        
        if not token_info:
            print(f"Token not found: {args.identifier}")
            return 1
        
        if 'error' in token_info:
            print(f"Error: {token_info['error']}")
            return 1
        
        if args.format == 'json':
            print(json.dumps(token_info, indent=2))
        else:
            # Detailed format
            print(f"Token Information:")
            print(f"  ID: {token_info['id']}")
            print(f"  Name: {token_info['name']}")
            print(f"  Description: {token_info['description'] or 'None'}")
            print(f"  Permissions: {token_info['permissions']}")
            print(f"  Rate Limit: {token_info['rate_limit']} requests/hour")
            print(f"  Active: {'Yes' if token_info['is_active'] else 'No'}")
            print(f"  Created: {datetime.fromisoformat(token_info['created_at']).strftime('%Y-%m-%d %H:%M:%S')}")
            
            if token_info['last_used_at']:
                print(f"  Last Used: {datetime.fromisoformat(token_info['last_used_at']).strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print(f"  Last Used: Never")
            
            print(f"  Usage Count: {token_info['usage_count']}")
            
            if token_info['expires_at']:
                expires = datetime.fromisoformat(token_info['expires_at'])
                print(f"  Expires: {expires.strftime('%Y-%m-%d %H:%M:%S')}")
                if expires < datetime.now():
                    print("    ⚠️  EXPIRED")
            else:
                print(f"  Expires: Never")
            
            if token_info['allowed_tools']:
                print(f"  Allowed Tools: {', '.join(token_info['allowed_tools'])}")
            else:
                print(f"  Allowed Tools: All")
            
            if token_info['ip_whitelist']:
                print(f"  IP Whitelist: {', '.join(token_info['ip_whitelist'])}")
            else:
                print(f"  IP Whitelist: All IPs allowed")
            
            if not token_info['is_active']:
                print(f"  Revoked: {datetime.fromisoformat(token_info['revoked_at']).strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"  Revoked By: {token_info['revoked_by']}")
                print(f"  Revoked Reason: {token_info['revoked_reason']}")
            
            # Usage statistics
            usage_stats = token_info.get('usage_stats', {})
            if usage_stats and not usage_stats.get('error'):
                print(f"\n24-Hour Usage Statistics:")
                print(f"  Total Requests: {usage_stats['total_requests']}")
                print(f"  Successful Requests: {usage_stats['successful_requests']}")
                print(f"  Error Rate: {usage_stats['error_rate']:.2%}")
                if usage_stats['avg_response_time_ms']:
                    print(f"  Avg Response Time: {usage_stats['avg_response_time_ms']:.1f}ms")
                
                if usage_stats['tools_usage']:
                    print(f"  Top Tools Used:")
                    for tool in usage_stats['tools_usage'][:5]:
                        print(f"    {tool['tool_name']}: {tool['count']} requests")
        
        return 0
    
    def revoke_token(self, args):
        """Revoke a token."""
        if not args.force:
            response = input(f"Are you sure you want to revoke token '{args.identifier}'? (y/N): ")
            if response.lower() != 'y':
                print("Revocation cancelled.")
                return 0
        
        success, message = self.manager.revoke_token(
            args.identifier,
            revoked_by=args.revoked_by or "cli",
            reason=args.reason or "Manual revocation via CLI"
        )
        
        if success:
            print(f"✓ {message}")
        else:
            print(f"✗ Error: {message}")
            return 1
        
        return 0
    
    def rotate_token(self, args):
        """Rotate a token."""
        if not args.force:
            response = input(f"Are you sure you want to rotate token '{args.identifier}'? (y/N): ")
            if response.lower() != 'y':
                print("Rotation cancelled.")
                return 0
        
        success, message, new_token = self.manager.rotate_token(
            args.identifier,
            revoked_by=args.revoked_by or "cli"
        )
        
        if success:
            print(f"✓ {message}")
            print(f"New Token: {new_token}")
            print("\n⚠️  IMPORTANT: Save this new token securely. The old token is now revoked!")
        else:
            print(f"✗ Error: {message}")
            return 1
        
        return 0
    
    def analytics(self, args):
        """Show system analytics."""
        analytics = self.manager.get_analytics(hours=args.hours)
        
        if 'error' in analytics:
            print(f"Error: {analytics['error']}")
            return 1
        
        if args.format == 'json':
            print(json.dumps(analytics, indent=2))
        else:
            print(f"System Analytics ({args.hours} hours):")
            print(f"  Total Tokens: {analytics['total_tokens']}")
            print(f"  Active Tokens: {analytics['active_tokens']}")
            print(f"  Total Requests: {analytics['total_requests']}")
            
            if analytics['recent_usage']:
                print(f"\nMost Active Tokens:")
                for usage in analytics['recent_usage'][:10]:
                    print(f"  {usage['token_name']}: {usage['requests']} requests")
            else:
                print(f"\nNo recent usage found.")
        
        return 0
    
    def cleanup(self, args):
        """Clean up expired tokens and old records."""
        if not args.force:
            response = input("Are you sure you want to clean up expired tokens? (y/N): ")
            if response.lower() != 'y':
                print("Cleanup cancelled.")
                return 0
        
        expired_tokens, cleaned_records = self.manager.cleanup_expired_tokens()
        
        print(f"Cleanup completed:")
        print(f"  Expired tokens revoked: {expired_tokens}")
        print(f"  Old usage records cleaned: {cleaned_records}")
        
        return 0


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="EnactAI Token Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a standard token
  python token_cli.py create "My API Token" --description "For my application"
  
  # Create an admin token with restrictions
  python token_cli.py create "Admin Token" --permissions admin --rate-limit 5000 --expires-in-days 30
  
  # Create a read-only token for specific tools
  python token_cli.py create "Analytics Token" --permissions read_only --allowed-tools "get_bill,search_bills"
  
  # List all tokens
  python token_cli.py list
  
  # Show token details
  python token_cli.py show "My API Token"
  
  # Revoke a token
  python token_cli.py revoke "token_id_here" --reason "Compromised"
  
  # Rotate a token
  python token_cli.py rotate "My API Token"
  
  # View analytics
  python token_cli.py analytics --hours 72
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create token command
    create_parser = subparsers.add_parser('create', help='Create a new token')
    create_parser.add_argument('name', help='Token name')
    create_parser.add_argument('--description', help='Token description')
    create_parser.add_argument('--permissions', choices=['read_only', 'standard', 'admin'], 
                              default='standard', help='Permission level')
    create_parser.add_argument('--rate-limit', type=int, default=1000, 
                              help='Requests per hour (default: 1000)')
    create_parser.add_argument('--allowed-tools', help='Comma-separated list of allowed tools')
    create_parser.add_argument('--ip-whitelist', help='Comma-separated list of allowed IPs/CIDR blocks')
    create_parser.add_argument('--expires-in-days', type=int, help='Token expiration in days')
    
    # List tokens command
    list_parser = subparsers.add_parser('list', help='List all tokens')
    list_parser.add_argument('--include-inactive', action='store_true', 
                            help='Include revoked/inactive tokens')
    list_parser.add_argument('--format', choices=['table', 'json'], default='table',
                            help='Output format')
    
    # Show token command
    show_parser = subparsers.add_parser('show', help='Show detailed token information')
    show_parser.add_argument('identifier', help='Token ID or name')
    show_parser.add_argument('--format', choices=['detail', 'json'], default='detail',
                            help='Output format')
    
    # Revoke token command
    revoke_parser = subparsers.add_parser('revoke', help='Revoke a token')
    revoke_parser.add_argument('identifier', help='Token ID or name')
    revoke_parser.add_argument('--reason', help='Reason for revocation')
    revoke_parser.add_argument('--revoked-by', help='Who is revoking the token')
    revoke_parser.add_argument('--force', action='store_true', help='Skip confirmation')
    
    # Rotate token command
    rotate_parser = subparsers.add_parser('rotate', help='Rotate a token (create new, revoke old)')
    rotate_parser.add_argument('identifier', help='Token ID or name')
    rotate_parser.add_argument('--revoked-by', help='Who is rotating the token')
    rotate_parser.add_argument('--force', action='store_true', help='Skip confirmation')
    
    # Analytics command
    analytics_parser = subparsers.add_parser('analytics', help='View system analytics')
    analytics_parser.add_argument('--hours', type=int, default=24, 
                                 help='Time period in hours (default: 24)')
    analytics_parser.add_argument('--format', choices=['detail', 'json'], default='detail',
                                 help='Output format')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up expired tokens and old records')
    cleanup_parser.add_argument('--force', action='store_true', help='Skip confirmation')
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Initialize CLI
    cli = TokenCLI()
    
    # Execute command
    try:
        if args.command == 'create':
            return cli.create_token(args)
        elif args.command == 'list':
            return cli.list_tokens(args)
        elif args.command == 'show':
            return cli.show_token(args)
        elif args.command == 'revoke':
            return cli.revoke_token(args)
        elif args.command == 'rotate':
            return cli.rotate_token(args)
        elif args.command == 'analytics':
            return cli.analytics(args)
        elif args.command == 'cleanup':
            return cli.cleanup(args)
        else:
            print(f"Unknown command: {args.command}")
            return 1
    
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())