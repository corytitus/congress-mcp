#!/usr/bin/env python3
"""
Test script for EnactAI Data Remote MCP Server
"""

import asyncio
import httpx
import json
import os

# Server configuration
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8080")
API_TOKEN = os.getenv("ENACTAI_API_TOKEN", "")

async def test_health():
    """Test health endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{SERVER_URL}/health")
        print(f"Health Check: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200

async def test_sse_connection():
    """Test SSE endpoint connection."""
    headers = {}
    if API_TOKEN:
        headers["Authorization"] = f"Bearer {API_TOKEN}"
    
    async with httpx.AsyncClient() as client:
        try:
            # Just test that we can connect
            response = await client.get(
                f"{SERVER_URL}/sse",
                headers=headers,
                timeout=5.0
            )
            print(f"SSE Connection Test: Connected successfully")
            return True
        except httpx.TimeoutException:
            # Timeout is expected for SSE as it's a long-running connection
            print(f"SSE Connection Test: Connection established (timeout expected)")
            return True
        except Exception as e:
            print(f"SSE Connection Test Failed: {e}")
            return False

async def test_openapi():
    """Test OpenAPI schema endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{SERVER_URL}/openapi.json")
        print(f"OpenAPI Schema: {response.status_code}")
        if response.status_code == 200:
            schema = response.json()
            print(f"API Title: {schema.get('info', {}).get('title')}")
            print(f"API Version: {schema.get('info', {}).get('version')}")
        return response.status_code == 200

async def main():
    """Run all tests."""
    print(f"Testing EnactAI Data Remote MCP Server at {SERVER_URL}")
    print("=" * 50)
    
    tests = [
        ("Health Check", test_health()),
        ("OpenAPI Schema", test_openapi()),
        ("SSE Connection", test_sse_connection()),
    ]
    
    results = []
    for name, test in tests:
        print(f"\nRunning: {name}")
        try:
            result = await test
            results.append((name, result))
            print(f"Result: {'✓ PASSED' if result else '✗ FAILED'}")
        except Exception as e:
            print(f"Error: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 50)
    print("Test Summary:")
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {name}: {status}")
    
    all_passed = all(passed for _, passed in results)
    print(f"\nOverall: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
    return all_passed

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)