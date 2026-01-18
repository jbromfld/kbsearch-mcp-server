"""
MCP Tool for CI/CD Database Queries

Refactored to use two-phase NL2SQL with distributed caching:
1. query_cicd_prepare - Slot extraction, cache check, schema fetch
2. query_cicd_execute - SQL execution and caching
"""

import os
import requests
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

# API endpoints
NL2SQL_PREPARE_URL = os.getenv("NL2SQL_PREPARE_URL", "http://localhost:8088/prepare")
NL2SQL_EXECUTE_URL = os.getenv("NL2SQL_EXECUTE_URL", "http://localhost:8088/execute")
NL2SQL_TIMEOUT = int(os.getenv("NL2SQL_TIMEOUT", "30"))  # Increased for LLM generation

# Optional: User identification for cache attribution
USER_ID = os.getenv("USER_ID", "unknown")


def _add_summary_stats(results: List[Dict]) -> Dict[str, Any]:
    """Add summary statistics based on result type"""
    if not results:
        return {}

    first_row = results[0]

    # Deployment stats
    if 'deploy_result' in first_row:
        total = len(results)
        successes = sum(1 for r in results if r.get('deploy_result') == 'SUCCESS')
        failures = sum(1 for r in results if r.get('deploy_result') == 'FAILURE')
        success_rate = round((successes / total * 100) if total > 0 else 0, 1)

        return {
            "type": "deployment",
            "total": total,
            "successes": successes,
            "failures": failures,
            "success_rate": f"{success_rate}%"
        }

    # Test stats
    elif 'tests_passed' in first_row or 'test_type' in first_row:
        total_tests = sum(r.get('tests_passed', 0) + r.get('tests_failed', 0) for r in results)
        total_passed = sum(r.get('tests_passed', 0) for r in results)
        total_failed = sum(r.get('tests_failed', 0) for r in results)
        pass_rate = round((total_passed / total_tests * 100) if total_tests > 0 else 0, 1)

        return {
            "type": "test",
            "test_runs": len(results),
            "total_tests": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "pass_rate": f"{pass_rate}%"
        }

    # Generic
    return {"type": "generic", "row_count": len(results)}


def _format_as_readable_list(results: List[Dict], summary: Dict[str, Any]) -> str:
    """Format results as readable bullet points with proper spacing"""
    if not results:
        return "No results found."

    result_type = summary.get("type", "generic")
    lines = []

    # Add summary header
    if result_type == "deployment":
        lines.append(f"**Found {summary['total']} deployments: {summary['successes']} successful, {summary['failures']} failed ({summary['success_rate']} success rate)**\n")

        for i, r in enumerate(results, 1):
            date_str = str(r.get('date', 'N/A'))[:16] if r.get('date') else 'N/A'
            result_icon = "✓" if r.get('deploy_result') == 'SUCCESS' else "✗"
            lines.append(f"{i}. **{r.get('app_name', 'N/A')}** {r.get('app_version', 'N/A')}")
            lines.append(f"   - Environment: {r.get('deploy_env', 'N/A')}")
            lines.append(f"   - Result: {result_icon} {r.get('deploy_result', 'N/A')}")
            lines.append(f"   - Date: {date_str}")
            lines.append(f"   - Deployed by: {r.get('deployed_by', 'N/A')}")
            lines.append("")  # Blank line between entries

    elif result_type == "test":
        lines.append(f"**Found {summary['test_runs']} test runs: {summary['total_tests']} total tests, {summary['passed']} passed, {summary['failed']} failed ({summary['pass_rate']} pass rate)**\n")

        for i, r in enumerate(results, 1):
            date_str = str(r.get('date', 'N/A'))[:16] if r.get('date') else 'N/A'
            duration = r.get('test_duration_seconds', 0)
            duration_str = f"{duration}s" if duration else "N/A"
            has_failures = r.get('tests_failed', 0) > 0
            result_icon = "✗" if has_failures else "✓"

            lines.append(f"{i}. **{r.get('app_name', 'N/A')}** {r.get('app_version', 'N/A')}")
            lines.append(f"   - Test Type: {r.get('test_type', 'N/A')}")
            lines.append(f"   - Results: {result_icon} {r.get('tests_passed', 0)} passed, {r.get('tests_failed', 0)} failed, {r.get('tests_skipped', 0)} skipped")
            lines.append(f"   - Duration: {duration_str}")
            lines.append(f"   - Date: {date_str}")
            lines.append("")  # Blank line between entries

    else:
        # Generic format
        lines.append(f"**Found {summary.get('row_count', len(results))} results**\n")

        for i, r in enumerate(results, 1):
            lines.append(f"{i}. Result:")
            for key, value in r.items():
                lines.append(f"   - {key}: {value}")
            lines.append("")  # Blank line between entries

    return "\n".join(lines)


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

        PRESENTATION INSTRUCTIONS:
        The response includes a 'formatted_results' field with pre-formatted, readable results.
        Simply display this field directly to the user - it's already formatted with proper spacing.
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
                # Cache hit - return results with summary stats and formatted table
                results = data.get("results", [])
                summary = _add_summary_stats(results)
                formatted_table = _format_as_readable_list(results, summary)

                return {
                    "status": "success",
                    "cached": True,
                    "results": results,
                    "summary": summary,
                    "formatted_results": formatted_table,
                    "sql": data.get("sql"),
                    "message": "Query results retrieved from cache. Display the 'formatted_results' to the user."
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
                "error": f"CI/CD database service returned error: {e.response.status_code}",
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
        - Returns the query results with summary statistics
        - Caches the SQL pattern so future similar queries are instant

        Returns:
        - status="success" + results → Show results to user
        - status="error" → SQL had an error, review and fix

        PRESENTATION INSTRUCTIONS:
        The response includes a 'formatted_results' field with pre-formatted, readable results.
        Simply display this field directly to the user - it's already formatted with proper spacing.
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
                # Return results with summary stats and formatted table
                results = data.get("results", [])
                summary = _add_summary_stats(results)
                formatted_table = _format_as_readable_list(results, summary)

                return {
                    "status": "success",
                    "results": results,
                    "summary": summary,
                    "formatted_results": formatted_table,
                    "sql": data.get("sql"),
                    "cached": data.get("cached", False),
                    "message": f"Query executed successfully. {'Cached for future use. ' if data.get('cached') else ''}Display the 'formatted_results' to the user."
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
                "error": f"CI/CD database service returned error: {e.response.status_code}",
                "details": e.response.text if e.response else None
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"Error executing SQL: {str(e)}"
            }
    