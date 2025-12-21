import os
import requests
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

NL2SQL_URL = os.getenv("NL2SQL_SERVICE_URL", "http://localhost:8088/query")
NL2SQL_TIMEOUT = int(os.getenv("NL2SQL_TIMEOUT", "5"))

def register(mcp):
    @mcp.tool(
        name="query_cicd_data",
        description="""Query the CI/CD database using natural language.

When to use:
- Use this tool when answering questions about the CI/CD pipeline.
- Use this tool when answering questions about the CI/CD database.

Output:
- Returns database query results with the generated SQL."""
    )
    def query_cicd_data(question: str) -> Dict[str, Any]:
        """Query the CI/CD database using natural language to SQL conversion."""
        try:
            resp = requests.post(
                NL2SQL_URL,
                json={"question": question},
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