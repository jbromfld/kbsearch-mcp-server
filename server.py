from fastmcp import FastMCP
from registry import register_tools
from dotenv import load_dotenv
import os
import sys

load_dotenv()

mcp = FastMCP(os.getenv("MCP_SERVER_NAME", "ci-knowledge-mcp"))

register_tools(mcp)

if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "stdio")

    if transport == "http":
        import logging
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.requests import Request

        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logger = logging.getLogger(__name__)

        # Add request logging middleware
        class RequestLoggingMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                logger.info(f"Request: {request.method} {request.url.path}")
                logger.info(f"Headers: {dict(request.headers)}")
                if request.method == "POST":
                    body = await request.body()
                    logger.info(f"Body: {body[:500]}")  # First 500 chars
                    # Rebuild request with body
                    from starlette.requests import Request as StarletteRequest
                    scope = request.scope
                    scope["body"] = body
                    request = StarletteRequest(scope, receive=request.receive, send=request._send)

                response = await call_next(request)
                logger.info(f"Response status: {response.status_code}")
                return response

        host = os.getenv("MCP_HTTP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_HTTP_PORT", "8080"))

        print(f"Starting MCP server in HTTP mode on {host}:{port}", file=sys.stderr)
        print(f"MCP endpoint: http://{host}:{port}/mcp", file=sys.stderr)

        # Get the HTTP app and add middleware
        app = mcp.http_app()
        app.add_middleware(RequestLoggingMiddleware)

        # Run with uvicorn
        import uvicorn
        uvicorn.run(app, host=host, port=port, log_level="info")
    else:
        print("Starting MCP server in STDIO mode", file=sys.stderr)
        mcp.run()