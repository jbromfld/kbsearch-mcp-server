import os
import sys
import uvicorn
from fastmcp import FastMCP
from registry import register_tools
from dotenv import load_dotenv


load_dotenv()

mcp = FastMCP(os.getenv("MCP_SERVER_NAME", "cicd-mcp"))
register_tools(mcp)

if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "stdio")

    if transport == "http":
        host = os.getenv("MCP_HTTP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_HTTP_PORT", "8080"))

        print(
            f"Starting MCP server in HTTP mode on {host}:{port}", file=sys.stderr)
        print(f"MCP endpoint: http://{host}:{port}/mcp", file=sys.stderr)

        app = mcp.http_app()

        uvicorn.run(app, host=host, port=port, log_level="info")
    else:
        print("Starting MCP server in STDIO mode", file=sys.stderr)
        mcp.run()
