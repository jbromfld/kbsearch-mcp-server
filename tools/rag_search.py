import os
import requests
from mcp.types import Tool
from dotenv import load_dotenv

load_dotenv()

RAG_URL = os.getenv("RAG_SERVICE_URL", "http://localhost:8000/search")
RAG_TIMEOUT = int(os.getenv("RAG_TIMEOUT", "5"))

def handler(args):
    try:
        resp = requests.post(
            RAG_URL,
            json={"query": args["query"]},
            timeout=RAG_TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json()

        return {
            "allowed_to_answer": data.get("allowed_to_answer", False),
            "documents": data.get("documents", []),
            "citations": data.get("citations", [])
        }
    except requests.exceptions.Timeout:
        return {
            "allowed_to_answer": False,
            "error": "Knowledge base search timed out. Please try again."
        }
    except requests.exceptions.ConnectionError:
        return {
            "allowed_to_answer": False,
            "error": "Could not connect to knowledge base service. Service may be down."
        }
    except requests.exceptions.HTTPError as e:
        return {
            "allowed_to_answer": False,
            "error": f"Knowledge base service returned an error: {e.response.status_code}"
        }
    except requests.exceptions.RequestException as e:
        return {
            "allowed_to_answer": False,
            "error": f"Error searching knowledge base: {str(e)}"
        }

rag_search = Tool(
    name="search_knowledge_base",
    description="""
        Search the internal knowledge base for authoritative information.

        When to use:
        - Use this tool before answering any technical, procedural, or "how-to" question.
        - Use this tool when factual accuracy matters.

        Constraints:
        - Do NOT answer from general knowledge without calling this tool first.
        - If no relevant documents are returned, the agent must say that no information was found.

        Output:
        - Returns retrieved documents with citations.
        """,
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language search query"
            }
        },
        "required": ["query"]
    },
    handler=handler
)