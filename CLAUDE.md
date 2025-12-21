# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an MCP (Model Context Protocol) server that exposes two tools for querying internal knowledge systems:
1. **Knowledge Base Search** - Semantic search against a RAG (Retrieval Augmented Generation) service
2. **CI/CD Database Query** - Natural language to SQL queries against a CI/CD database

The server acts as a middleware layer between Claude AI and backend data services, providing a standardized MCP interface.

## Architecture

### Core Components

**server.py** - Entry point that initializes the MCP server and registers all tools via the registry pattern.

**registry.py** - Centralized tool registration. All tools are imported and registered here using `server.add_tool()`. This pattern keeps the main server file clean and makes it easy to add/remove tools.

**tools/** - Each tool is a separate module that defines:
- A `handler(args)` function that implements the tool logic
- A `Tool` object with name, description, input schema, and handler
- All tools follow the same structure and use `allowed_to_answer` pattern to signal whether the tool can provide an answer

### Tool Response Pattern

Both tools follow a consistent response structure:
- `allowed_to_answer: bool` - Whether the tool successfully retrieved information
- On success: Additional fields like `documents`, `citations`, `rows`, `sql`
- On error: `error: str` with a descriptive message

Tools gracefully handle all request exceptions (timeout, connection errors, HTTP errors) and return structured error responses instead of crashing.

### Environment Configuration

All service URLs and timeouts are configured via environment variables using python-dotenv:
- Copy `.env.example` to `.env` and customize as needed
- Each tool calls `load_dotenv()` and uses `os.getenv()` with fallback defaults
- Never commit `.env` (it's in .gitignore)

## Development Commands

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your service URLs
```

### Running the Server
```bash
# Run locally (stdio transport for MCP clients)
python server.py

# The server expects two backend services:
# - RAG service at RAG_SERVICE_URL (default: http://localhost:8000/search)
# - NL2SQL service at NL2SQL_SERVICE_URL (default: http://localhost:8088/query)
```

### Testing
```bash
# Test files are in test/ directory
# test/server.py - Simple FastMCP test server
# test/client.py - Example client for testing tools
python test/client.py
```

## Adding New Tools

1. Create a new file in `tools/` (e.g., `tools/my_tool.py`)
2. Define a handler function and Tool object following the existing pattern
3. Import and register in `registry.py`
4. Add any new environment variables to `.env.example`

Example structure:
```python
import os
import requests
from mcp.types import Tool
from dotenv import load_dotenv

load_dotenv()

def handler(args):
    try:
        # Tool logic here
        return {"allowed_to_answer": True, "data": result}
    except Exception as e:
        return {"allowed_to_answer": False, "error": str(e)}

my_tool = Tool(
    name="tool_name",
    description="Detailed description with 'When to use' and 'Constraints'",
    input_schema={"type": "object", "properties": {...}, "required": [...]},
    handler=handler
)
```

## Tool Descriptions

Tool descriptions should be comprehensive and include:
- **When to use** - Clear guidance on when the tool should be invoked
- **Constraints** - Important rules (e.g., "Do NOT answer from general knowledge without calling this tool first")
- **Output** - What the tool returns

This helps the AI agent understand when and how to use each tool effectively.
