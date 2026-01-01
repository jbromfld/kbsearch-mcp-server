#!/usr/bin/env python3
"""Test the rag_search tool directly."""

import sys
sys.path.insert(0, '/Users/jbromfield/workspace/kbsearch-mcp-server')

from tools import rag_search

# Mock MCP object
class MockMCP:
    def tool(self, name=None, description=None):
        def decorator(func):
            print(f"\n[Mock MCP] Registered tool: {name or func.__name__}")
            print(f"[Mock MCP] Description: {description[:100] if description else 'None'}...")
            # Store the function globally so we can call it
            globals()[func.__name__] = func
            return func
        return decorator

# Register tools
mcp = MockMCP()
rag_search.register(mcp)

# Test the tool
print("\n" + "=" * 80)
print("TESTING search_knowledge_base TOOL")
print("=" * 80)

try:
    result = search_knowledge_base("What are the benefits of OpenAI GPT-5.2?", top_k=2)
    print(f"\nResult type: {type(result)}")
    print("\n" + "-" * 80)
    print("TOOL OUTPUT:")
    print("-" * 80)
    if isinstance(result, str):
        # Show first 1000 chars
        print(result[:1000])
        if len(result) > 1000:
            print(f"\n[...truncated {len(result) - 1000} more characters...]")
    else:
        print(f"ERROR: Expected string, got {type(result)}")
        print(result)
except Exception as e:
    print(f"\nERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
