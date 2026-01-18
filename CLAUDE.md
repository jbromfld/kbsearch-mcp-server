# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an MCP (Model Context Protocol) server that exposes two tools for querying internal knowledge systems:
1. **Knowledge Base Search** - Semantic search against a RAG (Retrieval Augmented Generation) service
2. **CI/CD Database Query** - Natural language to SQL queries against a CI/CD database

The server acts as a middleware layer between Claude AI and backend data services, providing a standardized MCP interface.

## Architecture

### Core Components

**server.py** - Entry point that initializes the FastMCP server and registers all tools via the registry pattern. Supports both STDIO (local) and HTTP (remote) transports.

**registry.py** - Centralized tool registration. All tools are imported and registered here. This pattern keeps the main server file clean and makes it easy to add/remove tools.

**auth.py** - Username validation helper (currently not integrated into HTTP mode due to FastMCP's middleware limitations). For production deployments, authentication should be handled at the infrastructure layer (reverse proxy, API gateway) rather than in the application.

**tools/** - Each tool is a separate module that defines:
- A `register(mcp)` function that registers the tool with the FastMCP server
- Tool implementation using `@mcp.tool()` decorator
- All tools follow the same structure and return structured responses

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

### Running the Server Locally (STDIO mode)
```bash
# Ensure MCP_TRANSPORT=stdio in .env (or unset, as it's the default)
python server.py

# The server expects two backend services:
# - RAG service at RAG_SERVICE_URL (default: http://localhost:8000/query)
# - NL2SQL service at NL2SQL_SERVICE_URL (default: http://localhost:8088/query)
```

### Running the Server in HTTP Mode
```bash
# Set environment variables
export MCP_TRANSPORT=http
export MCP_HTTP_PORT=8080

# Optional: Restrict to specific users
export ALLOWED_USERS=alice,bob,charlie

# Run server
python server.py

# Test health endpoint
curl http://localhost:8080/health

# Test with username header
curl -H "X-GitHub-User: alice" \
  http://localhost:8080/mcp
```

## Deployment

### Docker Deployment (Recommended)

The server can be deployed as a Docker container for remote access on your intranet.

#### Building the Image
```bash
docker build -t mcp-server:latest .
```

#### Using Docker Compose
```bash
# Edit .env with your configuration
cp .env.example .env
# Set MCP_TRANSPORT=http and configure backend service URLs

# Start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

#### Manual Docker Run
```bash
docker run -d \
  --name mcp-server \
  -p 8080:8080 \
  --env-file .env \
  -e MCP_TRANSPORT=http \
  mcp-server:latest
```

### Authentication & Security

For production deployments, authentication should be handled at the infrastructure layer rather than in the application:

#### Recommended Approaches

**1. Reverse Proxy with Authentication (Recommended)**

Deploy nginx or Traefik in front of the MCP server:

```nginx
# nginx example
server {
    listen 443 ssl;
    server_name mcp.internal.company.com;

    # Require client certificates or basic auth
    ssl_client_certificate /path/to/ca.crt;
    ssl_verify_client on;

    # Or use basic auth
    # auth_basic "MCP Server";
    # auth_basic_user_file /etc/nginx/.htpasswd;

    location / {
        proxy_pass http://mcp-server:8080;
        proxy_set_header X-GitHub-User $ssl_client_s_dn_cn;  # From client cert
        # Or from basic auth: $remote_user
    }
}
```

**2. API Gateway**

Use an API gateway (Kong, AWS API Gateway, Azure API Management) that:
- Validates OAuth/JWT tokens
- Enforces rate limiting
- Provides audit logging
- Routes to the MCP server

**3. Network-Level Security**

- Deploy on a private subnet/VPN
- Use firewall rules to restrict access
- Require VPN connection for access

#### VSCode/Cursor Configuration

Users configure their editor to connect to the remote MCP server:

**.cursor/mcp.json** or VSCode equivalent:
```json
{
  "mcpServers": {
    "company-knowledge": {
      "url": "https://mcp.internal.company.com/mcp",
      "headers": {
        "X-GitHub-User": "your-github-username"
      },
      "description": "Internal knowledge base and CI/CD data"
    }
  }
}
```

The `X-GitHub-User` header is optional and used for audit logging at the proxy/gateway level. Users can find their GitHub username with:
```bash
git config user.name
# or
gh api user --jq .login
```

### Kubernetes Deployment

For production Kubernetes deployment:

1. Create a ConfigMap for non-sensitive configuration
2. Create a Secret for backend service URLs (if sensitive)
3. Deploy as a Deployment with 2+ replicas for HA
4. Create a Service (ClusterIP or LoadBalancer)
5. Optional: Add an Ingress with TLS termination

Example manifest structure:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-server
spec:
  replicas: 2
  selector:
    matchLabels:
      app: mcp-server
  template:
    metadata:
      labels:
        app: mcp-server
    spec:
      containers:
      - name: mcp-server
        image: mcp-server:latest
        ports:
        - containerPort: 8080
        env:
        - name: MCP_TRANSPORT
          value: "http"
        envFrom:
        - configMapRef:
            name: mcp-config
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
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
