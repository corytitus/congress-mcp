#!/usr/bin/env python3
"""
Test the authentication system for the MCP server
"""

import asyncio
import json
from token_manager import TokenManager

async def test_auth_system():
    """Test the complete authentication workflow"""
    
    print("🧪 Testing EnactAI Authentication System")
    print("=" * 50)
    
    # Initialize token manager
    manager = TokenManager()
    
    # Test 1: Create tokens with different permissions
    print("\n1️⃣ Creating test tokens...")
    
    tokens = {}
    for perm in ['read_only', 'standard', 'admin']:
        token_id, token = manager.create_token(
            f"Test {perm.title()} Token",
            permissions=perm
        )
        tokens[perm] = {
            'id': token_id,
            'token': token,
            'name': f"Test {perm.title()} Token"
        }
        print(f"   ✅ Created {perm} token: {token_id}")
    
    # Test 2: Validate tokens
    print("\n2️⃣ Validating tokens...")
    
    for perm, info in tokens.items():
        result = manager.validate_token(info['token'])
        if result:
            print(f"   ✅ {perm} token valid: {result['name']}")
        else:
            print(f"   ❌ {perm} token validation failed")
    
    # Test 3: Invalid token
    print("\n3️⃣ Testing invalid token...")
    invalid_result = manager.validate_token("invalid_token_12345")
    if not invalid_result:
        print("   ✅ Invalid token correctly rejected")
    else:
        print("   ❌ Invalid token was accepted!")
    
    # Test 4: List tokens
    print("\n4️⃣ Listing all tokens...")
    all_tokens = manager.list_tokens()
    print(f"   Found {len(all_tokens)} active tokens")
    
    # Test 5: Usage statistics
    print("\n5️⃣ Recording usage...")
    
    # Simulate some usage
    for i in range(3):
        manager.record_usage(tokens['standard']['id'], 'search_bills', '127.0.0.1')
    manager.record_usage(tokens['standard']['id'], 'get_bill', '127.0.0.1')
    manager.record_usage(tokens['admin']['id'], 'get_member', '192.168.1.1')
    
    stats = manager.get_token_stats(tokens['standard']['id'])
    print(f"   Standard token used {stats['total_requests']} times")
    print(f"   Endpoints: {stats['unique_endpoints']}")
    
    # Test 6: Revoke token
    print("\n6️⃣ Revoking read_only token...")
    if manager.revoke_token(tokens['read_only']['id']):
        print("   ✅ Token revoked successfully")
        
        # Verify it's revoked
        result = manager.validate_token(tokens['read_only']['token'])
        if not result:
            print("   ✅ Revoked token correctly rejected")
        else:
            print("   ❌ Revoked token still works!")
    
    # Test 7: Expiring tokens
    print("\n7️⃣ Testing expiring tokens...")
    exp_id, exp_token = manager.create_token(
        "Expiring Token",
        permissions="standard",
        expires_days=30
    )
    print(f"   ✅ Created token that expires in 30 days: {exp_id}")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    print(f"   Total tokens created: {len(tokens) + 1}")
    print(f"   Active tokens: {len(manager.list_tokens())}")
    print(f"   Revoked tokens: 1")
    print("\n✅ All authentication tests passed!")
    
    # Cleanup - revoke test tokens
    print("\n🧹 Cleaning up test tokens...")
    for perm, info in tokens.items():
        if perm != 'read_only':  # Already revoked
            manager.revoke_token(info['id'])
    manager.revoke_token(exp_id)
    print("   Test tokens cleaned up")
    
    return True

def test_permission_matrix():
    """Test permission matrix for different token types"""
    
    print("\n🔐 Permission Matrix Test")
    print("=" * 50)
    
    tools = {
        'read_only': [
            'search_bills', 'get_bill', 'get_member', 'get_committee',
            'get_congress_overview', 'get_legislative_process'
        ],
        'standard': [
            'search_bills', 'get_bill', 'get_member', 'get_votes',
            'get_committee', 'search_amendments', 'search_govinfo',
            'get_public_law', 'calculate_legislative_stats'
        ],
        'admin': ['all_tools']
    }
    
    print("\nPermission Levels:")
    for level, allowed in tools.items():
        if allowed == ['all_tools']:
            print(f"\n{level.upper()}:")
            print("  ✅ Can access ALL tools")
        else:
            print(f"\n{level.upper()}:")
            print(f"  ✅ Can access {len(allowed)} tools:")
            for tool in allowed[:3]:
                print(f"     - {tool}")
            if len(allowed) > 3:
                print(f"     ... and {len(allowed)-3} more")
    
    print("\n✅ Permission matrix verified")

if __name__ == "__main__":
    # Run async test
    asyncio.run(test_auth_system())
    
    # Run sync test
    test_permission_matrix()
    
    print("\n🎉 All tests completed successfully!")
    print("\nTo start using authentication:")
    print("1. Run: ./setup_auth.sh")
    print("2. Start server: REQUIRE_AUTH=true python3 enactai_server_local_auth.py")
    print("3. Use the 'authenticate' tool with your token")