# Service Startup Guide

This guide explains how to start and manage all services needed for the CI/CD Knowledge Base MCP integration.

## Architecture

```
┌─────────────────┐
│   VS Code       │
│   Copilot       │
└────────┬────────┘
         │ MCP Protocol (SSE)
         │
         ▼
┌─────────────────────────────┐
│  MCP Server (port 8080)     │
│  - query_cicd_prepare       │
│  - query_cicd_execute       │
│  - rag_search               │
└────────┬────────────────────┘
         │
         ├─ HTTP Calls
         │
         ▼
┌─────────────────────────────┐     ┌─────────────────────────────┐
│  NL2SQL API (port 8088)     │     │  RAG Service (port 8000)    │
│  - POST /prepare            │     │  - POST /query              │
│  - POST /execute            │     │  - POST /feedback           │
│  - GET  /cache/*            │     └─────────────────────────────┘
└─────────────────────────────┘
```

## Quick Start

### 1. Start All Services

```bash
cd /Users/jbromfield/workspace/kbsearch-mcp-server
./start-all-services.sh start
```

This will start:
- ✅ RAG service on port 8000
- ✅ NL2SQL API on port 8088
- ✅ MCP server on port 8080

### 2. Reload MCP in VS Code

After starting services, reload the MCP connection:
- Open Command Palette (`Cmd+Shift+P`)
- Search for "MCP: Restart Servers"
- Or restart VS Code

### 3. Test the Integration

Ask Copilot:
```
"What were the last three deployments to prod?"
```

It should use the `query_cicd_prepare` tool automatically.

## Management Commands

### Check Status
```bash
./start-all-services.sh status
```

### View Logs
```bash
# All logs
./start-all-services.sh logs all

# Specific service
./start-all-services.sh logs rag
./start-all-services.sh logs nl2sql
./start-all-services.sh logs mcp
```

### Stop All Services
```bash
./start-all-services.sh stop
```

### Restart All Services
```bash
./start-all-services.sh restart
```

## Troubleshooting

### Port Already in Use

If you see "Port XXXX already in use":

```bash
# Check what's using the port
lsof -i :8080  # or :8088, :8000

# Kill the process
kill <PID>

# Then restart
./start-all-services.sh restart
```

### Service Won't Start

Check the logs:
```bash
# View logs
./start-all-services.sh logs <service>

# Log files location:
# - RAG:     .logs/rag.log
# - NL2SQL:  .logs/nl2sql.log
# - MCP:     .logs/mcp.log
```

### MCP Tools Not Available in VS Code

1. Check service status:
   ```bash
   ./start-all-services.sh status
   ```

2. Verify MCP server is responding:
   ```bash
   curl http://localhost:8080/mcp
   ```

3. Check VS Code MCP configuration:
   ```
   ~/Library/Application Support/Code/User/mcp.json
   ```

4. Restart VS Code MCP servers:
   - Command Palette → "MCP: Restart Servers"

### 404 on /query Endpoint

The `/query` endpoint doesn't exist. The correct flow is:
1. Copilot calls `query_cicd_prepare` MCP tool
2. MCP tool calls `/prepare` endpoint
3. If cache miss, Copilot generates SQL
4. Copilot calls `query_cicd_execute` MCP tool
5. MCP tool calls `/execute` endpoint

If you see 404s for `/query`, something is misconfigured to call the API directly instead of through MCP tools.

## Environment Variables

Services read from `.env` files in their respective directories:

### RAG Service
Location: `/Users/jbromfield/workspace/rag-mcp/.env`

### NL2SQL API
Location: `/Users/jbromfield/workspace/nl2sql-mcp/.env`
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/cicd_testing
PORT=8088
```

### MCP Server
Location: `/Users/jbromfield/workspace/kbsearch-mcp-server/.env`
```bash
NL2SQL_PREPARE_URL=http://localhost:8088/prepare
NL2SQL_EXECUTE_URL=http://localhost:8088/execute
RAG_SERVICE_URL=http://localhost:8000/query
MCP_TRANSPORT=http
MCP_HTTP_PORT=8080
```

## Available MCP Tools

### query_cicd_prepare
Prepares a natural language query for SQL generation.
- Checks cache first
- Returns results immediately if cached
- Returns schema context if cache miss

**Example:**
```
"Show me failed tests for frontend in the last week"
```

### query_cicd_execute
Executes generated SQL and caches it.
- Only used after `query_cicd_prepare` indicates SQL generation needed
- Caches successful queries for future use

### rag_search
Searches the knowledge base using RAG.

**Example:**
```
"How do I deploy to production?"
```

### query_cicd_cache_stats
Shows cache statistics (hits, popular queries, etc.)

### query_cicd_cache_list
Lists cached query patterns

## Development

### Manual Service Startup

If you need to start services individually:

```bash
# RAG service
cd /Users/jbromfield/workspace/rag-mcp
./setup-local.sh

# NL2SQL API
cd /Users/jbromfield/workspace/nl2sql-mcp
python app/api_server.py

# MCP server
cd /Users/jbromfield/workspace/kbsearch-mcp-server
.venv/bin/python server.py
```

### Using Docker Compose (Alternative)

```bash
cd /Users/jbromfield/workspace/kbsearch-mcp-server
docker-compose up
```

Note: This only starts the MCP server. You still need to start RAG and NL2SQL services separately.

## VS Code MCP Configuration

Location: `~/Library/Application Support/Code/User/mcp.json`

```json
{
  "servers": {
    "cicd-mcp": {
      "url": "http://localhost:8080/mcp",
      "type": "sse",
      "description": "MCP server with RAG search and CI/CD query tools"
    }
  },
  "inputs": []
}
```

## Health Checks

```bash
# RAG service
curl http://localhost:8000/health

# NL2SQL API
curl http://localhost:8088/health

# MCP server
curl http://localhost:8080/mcp
# Should return: {"error": "Not Acceptable: Client must accept text/event-stream"}
# This is expected - it means the server is running
```
