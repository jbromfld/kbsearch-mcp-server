# CICD Tools MCP Server

Minimal MCP (Model Context Protocol) server that provides two powerful tools for your development workflow:

## 🔧 Available Tools

### 1. Knowledge Base Search (RAG)
**Tool:** `search_knowledge_base`

Search through your organization's internal documentation and knowledge base using Retrieval-Augmented Generation (RAG). This tool:
- Searches across ingested documentation (Python docs, Java docs, JavaScript docs, NPM, Maven, AKS, CI/CD guides, etc.)
- Returns relevant chunks with citations and source URLs
- Uses hybrid search (semantic + keyword) with quality boosting based on user feedback
- Provides inline citations [1], [2] that you can reference in your answers
- Includes Query ID for submitting feedback to improve future results

**When to use:**
- "What is [technical concept]?" questions
- "How do I..." questions about tools, frameworks, or systems  
- Finding API documentation or code examples
- Questions about deployment, CI/CD, infrastructure
- Any question where internal documentation might exist

**Example queries:**
- "What is the recommended approach for AKS deployment?"
- "How do I configure the CI/CD pipeline?"
- "Explain the authentication flow"

### 2. CI/CD Database Query (NL2SQL)
**Tools:** `query_cicd_prepare` and `query_cicd_execute`

Convert natural language questions into SQL queries against your CI/CD database, with intelligent caching for instant responses. This two-step process:

**Step 1: Prepare (`query_cicd_prepare`)**
- Extracts query parameters (app name, environment, time range)
- Checks if this query pattern is cached
- If cached: returns results immediately
- If not cached: returns schema + instructions for SQL generation

**Step 2: Execute (`query_cicd_execute`)**  
- Takes the generated SQL and executes it
- Returns formatted results
- Caches the query pattern for future use

**When to use:**
- Questions about deployments, test results, or CI/CD history
- Time-based queries ("last week", "today", "last 5")
- Application-specific queries ("frontend", "api-gateway")
- Failure analysis and debugging

**Example queries:**
- "What was the last deployment for frontend to prod?"
- "Show me failures in the last week"
- "How many tests ran for api-gateway today?"
- "List the last 5 deployments to staging"

## Quick start
- Create a Python venv and install deps:

	python -m venv .venv
	source .venv/bin/activate
	pip install -r requirements.txt

- Start the server:

	export MCP_SERVER_NAME=ci-knowledge-mcp
	python server.py

	The server will print its listening URL/port to the console — note the base URL (for example `http://localhost:PORT`).

Editor integrations

### VS Code
VS Code supports MCP servers through the `.mcp.json` configuration file in your workspace root. This repository includes a pre-configured `.mcp.json` file.

1. Ensure the MCP server is running (see Quick start above)
2. The included `.mcp.json` file is already configured:
   ```json
   {
     "servers": {
       "cicd-mcp": {
         "url": "http://localhost:8080/mcp",
         "type": "sse",
         "description": "MCP server with RAG search and CI/CD query tools"
       }
     }
   }
   ```
3. VS Code will automatically detect and load MCP servers from `.mcp.json`
4. Open the GitHub Copilot chat panel to access the MCP tools
5. The tools will be available with the `mcp_cicd-mcp_` prefix:
   - `mcp_cicd-mcp_search_knowledge_base` - Search the internal knowledge base
   - `mcp_cicd-mcp_query_cicd_prepare` - Prepare CI/CD database queries
   - `mcp_cicd-mcp_query_cicd_execute` - Execute generated SQL queries
   - `mcp_cicd-mcp_submit_feedback` - Submit feedback on query results

**Note:** If the server is running on a different port, update the `url` field in `.mcp.json` accordingly.

### Cursor
Cursor has built-in support for MCP servers and can use the same `.mcp.json` configuration:

1. Ensure the MCP server is running (see Quick start above)
2. The `.mcp.json` file in your workspace root will be automatically detected
3. Alternatively, you can configure MCP servers manually:
   - Open Cursor Settings (Cmd+, on macOS)
   - Navigate to Features → MCP Servers
   - Click "Add Server" and enter:
     - Name: `cicd-mcp`
     - URL: `http://localhost:8080/mcp`
     - Type: `sse`
4. Restart Cursor to load the MCP server
5. Access the tools through Cursor's chat interface

### IntelliJ IDEA / Community Edition
IntelliJ support for MCP servers is available through compatible AI assistant plugins:

1. Install an AI assistant plugin that supports MCP (e.g., Continue, or other compatible plugins from JetBrains Marketplace)
2. Navigate to plugin settings:
   - File → Settings (Windows/Linux) or IntelliJ IDEA → Preferences (macOS)
   - Search for your AI plugin's settings
3. Add MCP server configuration:
   - Server Name: `cicd-mcp`
   - Server URL: `http://localhost:8080/mcp`
   - Protocol: SSE (Server-Sent Events)
4. Apply settings and restart IntelliJ
5. Access MCP tools through the AI assistant interface

**Note:** MCP support in IntelliJ may vary depending on the specific plugin used. Refer to your plugin's documentation for detailed configuration steps.

Notes
- If your editor/plugin requires an API key or other auth, check `server.py` and the server logs for supported auth options and configure accordingly.
- If you want to bind to a fixed port or host, modify `server.py` to call `mcp.run(host=..., port=...)` or consult the `fastmcp` docs for runtime options.

Contributions and issues
- See `registry.py` to add or remove registered tools.

