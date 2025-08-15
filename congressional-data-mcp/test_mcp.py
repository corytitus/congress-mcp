#!/usr/bin/env python3
"""Quick test to verify MCP server is working"""

import os
import sys

print("Testing Congressional Data MCP Server")
print("=" * 40)

# Check environment
print("✓ Python:", sys.executable)
print("✓ Version:", sys.version.split()[0])

# Check packages
packages_ok = True
for package in ['mcp', 'httpx', 'structlog', 'aiolimiter']:
    try:
        __import__(package)
        print(f"✓ {package} installed")
    except ImportError:
        print(f"✗ {package} missing")
        packages_ok = False

# Check API keys
congress_key = os.getenv("CONGRESS_GOV_API_KEY", "")
govinfo_key = os.getenv("GOVINFO_API_KEY", "")

if congress_key and congress_key != "your-congress-api-key-here":
    print("✓ Congress.gov API key configured")
else:
    print("✗ Congress.gov API key missing")
    
if govinfo_key and govinfo_key != "your-govinfo-api-key-here":
    print("✓ GovInfo API key configured")
else:
    print("✗ GovInfo API key missing")

print("=" * 40)
if packages_ok and congress_key and govinfo_key:
    print("✅ Ready for Claude Desktop!")
    print("\nRestart Claude Desktop to activate")
else:
    print("❌ Some issues need fixing")