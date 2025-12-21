from mcp.server import Server
from mcp_server.registry import register_tools
from dotenv import load_dotenv
import os

load_dotenv()

server = Server(os.getenv("MCP_SERVER_NAME", "ci-knowledge-mcp"))

register_tools(server)

if __name__ == "__main__":
    server.run()