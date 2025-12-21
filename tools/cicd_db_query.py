import os
import requests
from mcp.types import Tool
from dotenv import load_dotenv

load_dotenv()

NL2SQL_URL = os.getenv("NL2SQL_SERVICE_URL", "http://localhost:8088/query")
NL2SQL_TIMEOUT = int(os.getenv("NL2SQL_TIMEOUT", "5"))

def handler(args):
    try:
        resp = requests.post(
            NL2SQL_URL,
            json={"question": args["question"]},
            timeout=NL2SQL_TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json()

        if not data.get("allowed", False):
            return {"allowed_to_answer": False}

        return {
            "allowed_to_answer": True,
            "rows": data["rows"],
            "sql": data["sql"],
            "sources": ["ci_postgres"]
        }
    except requests.exceptions.Timeout:
        return {
            "allowed_to_answer": False,
            "error": "CI/CD database query timed out. Please try again."
        }
    except requests.exceptions.ConnectionError:
        return {
            "allowed_to_answer": False,
            "error": "Could not connect to CI/CD database service. Service may be down."
        }
    except requests.exceptions.HTTPError as e:
        return {
            "allowed_to_answer": False,
            "error": f"CI/CD database service returned an error: {e.response.status_code}"
        }
    except requests.exceptions.RequestException as e:
        return {
            "allowed_to_answer": False,
            "error": f"Error querying CI/CD database: {str(e)}"
        }

cicd_db_query = Tool(
    name="query_ci_data",
    description="""
        Query the CI/CD database using natural language.

        When to use:
        - Use this tool when answering questions about the CI/CD pipeline.
        - Use this tool when answering questions about the CI/CD database.
            - Use this tool when answering questions about the CI/CD pipeline.
        """,
    input_schema={
        "type": "object",
        "properties": {
            "question": {"type": "string"}
        },
        "required": ["question"]
    },
    handler=handler
)