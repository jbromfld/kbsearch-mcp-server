from fastmcp import FastMCP
from registry import register_tools
from dotenv import load_dotenv
import os

load_dotenv()

mcp = FastMCP(os.getenv("MCP_SERVER_NAME", "ci-knowledge-mcp"))

register_tools(mcp)

if __name__ == "__main__":
    mcp.run()