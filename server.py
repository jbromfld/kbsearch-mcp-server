from fastmcp import FastMCP
from pydantic_ai import Agent
import requests

mcp = FastMCP("My MCP Server")

@mcp.tool
def greet(name: str) -> str:
    return f"Hello, {name}!"


@mcp.tool
def search(query: str) -> str:
    url = "http://localhost:8000/query"
    headers = {"Content-Type": "application/json"}
    data = {"query": query}
    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    
    # Extract and format the answer
    answer = result.get("answer", "No answer found")
    sources = result.get("sources", [])
    
    # Format the response
    formatted = answer
    if sources:
        formatted += "\n\nSources:\n"
        for i, source in enumerate(sources, 1):
            formatted += f"{i}. {source.get('title', 'Unknown')} - {source.get('url', 'No URL')}\n"
    
    return formatted

if __name__ == "__main__":
    mcp.run()
    # mcp.run(transport="http", port=8088)
