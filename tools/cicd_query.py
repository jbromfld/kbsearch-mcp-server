"""
MCP Tool for CI/CD Database Queries

Refactored to use two-phase NL2SQL with distributed caching:
1. query_cicd_prepare - Slot extraction, cache check, schema fetch
2. query_cicd_execute - SQL execution and caching
"""

import os
import requests
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

# API endpoints
NL2SQL_PREPARE_URL = os.getenv("NL2SQL_PREPARE_URL", "http://localhost:8088/prepare")
NL2SQL_EXECUTE_URL = os.getenv("NL2SQL_EXECUTE_URL", "http://localhost:8088/execute")
NL2SQL_TIMEOUT = int(os.getenv("NL2SQL_TIMEOUT", "30"))  # Increased for LLM generation

# Optional: User identification for cache attribution
USER_ID = os.getenv("USER_ID", "unknown")


def register(mcp):

    @mcp.tool(
        name="query_cicd_prepare",
        description="""Prepare a CI/CD database query from natural language.

        ⚠️ This is STEP 1 of 2 for querying the CI/CD database.

        What it does:
        - Extracts query parameters (app name, environment, time range)
        - Checks if this query pattern is cached
        - Returns results directly if cached (DONE!)
        - If NOT cached: Returns schema + instructions for SQL generation

        IMPORTANT: If status="needs_generation", you MUST:
        1. Generate SQL based on the provided instruction
        2. Immediately call query_cicd_execute with the SQL

        Example queries:
        - "What was the last deployment for frontend to prod?"
        - "Show me failures in the last week"
        - "How many tests ran for api-gateway today?"
        - "List the last 5 deployments to staging"

        Outputs:
        - status="success" + results → Query complete, show results to user
        - status="needs_generation" → Generate SQL and call query_cicd_execute next
        """
    )
    def query_cicd_prepare(question: str) -> Dict[str, Any]:
        """
        Phase 1: Prepare NL query for SQL generation or return cached results.
        
        Args:
            question: Natural language question about CI/CD data
            
        Returns:
            Dictionary with either:
            - Direct results (cache hit)
            - Context for SQL generation (cache miss)
        """
        try:
            resp = requests.post(
                NL2SQL_PREPARE_URL,
                json={
                    "query": question,
                    "user_id": USER_ID
                },
                timeout=NL2SQL_TIMEOUT
            )
            resp.raise_for_status()
            data = resp.json()
            
            # Handle different response types
            status = data.get("status")
            
            if status == "success":
                # Cache hit - results ready
                return {
                    "status": "success",
                    "cached": True,
                    "results": data.get("results", []),
                    "row_count": data.get("row_count", 0),
                    "sql": data.get("sql"),
                    "cache_key": data.get("cache_key"),
                    "message": "Query results retrieved from cache"
                }
            
            elif status == "needs_generation":
                # Cache miss - need to generate SQL
                instruction = data.get("instruction", "")
                cache_key = data.get("cache_key")

                return {
                    "status": "ACTION_REQUIRED",
                    "action": "EXECUTE_SQL",
                    "cached": False,
                    "cache_key": cache_key,
                    "instruction": instruction,
                    "error": "⚠️ INCOMPLETE - SQL not executed yet",
                    "message": f"""❌ Query NOT complete - Action required!

📋 REQUIRED NEXT STEPS:
1. Generate SQL using the instruction below
2. Call query_cicd_execute(sql="YOUR_SQL", cache_key="{cache_key}", confirm_cache=true)
3. Return those results to the user

⚠️ DO NOT show SQL to user without executing it first!

📝 SQL Generation Instruction:
{instruction}

🔧 Example call:
query_cicd_execute(
    sql="SELECT * FROM deployment_data WHERE deploy_env='PROD' ORDER BY date DESC LIMIT 3",
    cache_key="{cache_key}",
    confirm_cache=true
)"""
                }
            
            elif status == "error":
                # Validation or other error
                return {
                    "status": "error",
                    "error": data.get("message", "Unknown error"),
                    "warnings": data.get("warnings", []),
                    "suggestions": data.get("suggestions", [])
                }
            
            else:
                return {
                    "status": "error",
                    "error": f"Unexpected status: {status}"
                }
        
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": "CI/CD database query preparation timed out. Please try again."
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Could not connect to CI/CD database service. Service may be down."
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"CI/CD database service returned an error: {e.response.status_code}",
                "details": e.response.text if e.response else None
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"Error preparing CI/CD query: {str(e)}"
            }
    
    
    @mcp.tool(
        name="query_cicd_execute",
        description="""Execute a generated SQL query against the CI/CD database.

        ⚠️ This is STEP 2 of 2 - REQUIRED after query_cicd_prepare returns "needs_generation"

        When to use:
        - query_cicd_prepare returned status="needs_generation"
        - You generated SQL based on the instruction it provided
        - Now call THIS tool to execute the SQL and get results

        Required args:
        - sql: The SQL query you generated (string)
        - cache_key: The cache_key from query_cicd_prepare (string)
        - confirm_cache: Whether to cache for future use (boolean, default: true)

        What it does:
        - Executes your SQL against the database
        - Returns the query results
        - Caches the SQL pattern so future similar queries are instant

        Returns:
        - status="success" + results → Show results to user
        - status="error" → SQL had an error, review and fix
        """
    )
    def query_cicd_execute(
        sql: str, 
        cache_key: str, 
        confirm_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Phase 2: Execute generated SQL and optionally cache it.
        
        Args:
            sql: The SQL query to execute
            cache_key: Cache key from query_cicd_prepare
            confirm_cache: Whether to cache this SQL for future queries
            
        Returns:
            Query results and execution metadata
        """
        try:
            resp = requests.post(
                NL2SQL_EXECUTE_URL,
                json={
                    "sql": sql,
                    "cache_key": cache_key,
                    "confirm_cache": confirm_cache,
                    "user_id": USER_ID
                },
                timeout=NL2SQL_TIMEOUT
            )
            resp.raise_for_status()
            data = resp.json()
            
            status = data.get("status")
            
            if status == "success":
                return {
                    "status": "success",
                    "results": data.get("results", []),
                    "row_count": data.get("row_count", 0),
                    "sql": data.get("sql"),
                    "cached": data.get("cached", False),
                    "cache_key": data.get("cache_key"),
                    "message": f"Query executed successfully. {'Cached for future use.' if data.get('cached') else ''}"
                }
            
            elif status == "error":
                return {
                    "status": "error",
                    "error": data.get("message", "SQL execution failed"),
                    "sql": sql,
                    "error_type": data.get("error_type")
                }
            
            else:
                return {
                    "status": "error",
                    "error": f"Unexpected status: {status}"
                }
        
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": "SQL execution timed out. Query may be too complex."
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Could not connect to CI/CD database service. Service may be down."
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"CI/CD database service returned an error: {e.response.status_code}",
                "details": e.response.text if e.response else None
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"Error executing SQL: {str(e)}"
            }
    
    
    @mcp.tool(
        name="query_cicd_cache_stats",
        description="""Get statistics about cached CI/CD queries.

        Shows:
        - Total number of cached query patterns
        - Total cache hits across all users
        - Most frequently used queries
        - Number of developers using the cache

        Useful for understanding query patterns and cache effectiveness.
        """
    )
    def query_cicd_cache_stats() -> Dict[str, Any]:
        """Get cache statistics for CI/CD queries."""
        try:
            resp = requests.get(
                f"{NL2SQL_PREPARE_URL.rsplit('/', 1)[0]}/cache/stats",
                timeout=NL2SQL_TIMEOUT
            )
            resp.raise_for_status()
            return resp.json()
        
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to fetch cache stats: {str(e)}"
            }
    
    
    @mcp.tool(
        name="query_cicd_cache_list",
        description="""List cached CI/CD query patterns.

        Shows recently used cached queries with:
        - Cache key (query pattern)
        - When it was created
        - When it was last used
        - How many times it's been used
        - Who created it

        Args:
        - limit: Maximum number of entries to return (default: 50)
        """
    )
    def query_cicd_cache_list(limit: int = 50) -> Dict[str, Any]:
        """List cached query patterns."""
        try:
            resp = requests.get(
                f"{NL2SQL_PREPARE_URL.rsplit('/', 1)[0]}/cache/list",
                params={"limit": limit},
                timeout=NL2SQL_TIMEOUT
            )
            resp.raise_for_status()
            return resp.json()
        
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to list cache: {str(e)}"
            }
