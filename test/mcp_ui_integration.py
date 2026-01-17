"""
MCP Tool with UI Integration for CI/CD Database Queries

Uses the official mcp_ui_server library to render results in rich, interactive formats:
- Tables for deployment/test data
- Charts for trends and statistics
- Cards for individual records
- Alerts for failures/warnings
"""

import os
import requests
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Import MCP UI components
from mcp_ui_server import (
    Container,
    Table,
    Alert,
    Stats,
    Code,
    Collapsible,
    Text,
    Divider
)

load_dotenv()

# API endpoints
NL2SQL_PREPARE_URL = os.getenv("NL2SQL_PREPARE_URL", "http://localhost:8088/prepare")
NL2SQL_EXECUTE_URL = os.getenv("NL2SQL_EXECUTE_URL", "http://localhost:8088/execute")
NL2SQL_TIMEOUT = int(os.getenv("NL2SQL_TIMEOUT", "30"))
USER_ID = os.getenv("USER_ID", "unknown")


def format_deployment_results(results: List[Dict], sql: str = None):
    """Format deployment results using MCP UI components"""
    
    if not results:
        return Alert(
            variant="info",
            title="No Results",
            message="No deployments found matching your query."
        )
    
    # Calculate statistics
    total = len(results)
    successes = sum(1 for r in results if r.get('deploy_result') == 'SUCCESS')
    failures = sum(1 for r in results if r.get('deploy_result') == 'FAILURE')
    success_rate = round((successes / total * 100) if total > 0 else 0, 1)
    
    # Build components list
    components = []
    
    # Add warning alert if there are failures
    if failures > 0:
        components.append(
            Alert(
                variant="warning",
                title="Deployment Failures Detected",
                message=f"Found {failures} failed deployment(s) in the results. Review the table below for details."
            )
        )
    
    # Add SQL collapsible if provided
    if sql:
        components.append(
            Collapsible(
                title="Generated SQL Query",
                collapsed=True,
                content=Code(
                    language="sql",
                    code=sql
                )
            )
        )
    
    # Add summary statistics
    components.append(
        Stats(
            items=[
                {"label": "Total Deployments", "value": str(total), "variant": "default"},
                {"label": "Successful", "value": str(successes), "variant": "success"},
                {"label": "Failed", "value": str(failures), "variant": "error"},
                {
                    "label": "Success Rate",
                    "value": f"{success_rate}%",
                    "variant": "success" if success_rate >= 90 else "warning" if success_rate >= 70 else "error"
                }
            ]
        )
    )
    
    # Build table data
    headers = ["App", "Version", "Environment", "Result", "Date", "Deployed By"]
    rows = []
    
    for r in results:
        # Format date
        date_str = str(r.get('date', 'N/A'))[:16] if r.get('date') else 'N/A'
        
        # Determine row styling
        result_status = r.get('deploy_result', 'UNKNOWN')
        row_variant = "success" if result_status == "SUCCESS" else "error" if result_status == "FAILURE" else "warning"
        
        rows.append({
            "cells": [
                r.get('app_name', 'N/A'),
                r.get('app_version', 'N/A'),
                r.get('deploy_env', 'N/A'),
                result_status,
                date_str,
                r.get('deployed_by', 'N/A')
            ],
            "variant": row_variant
        })
    
    # Add table
    components.append(
        Table(
            title="Deployment Results",
            headers=headers,
            rows=rows,
            sortable=True,
            filterable=True
        )
    )
    
    return Container(
        layout="vertical",
        components=components
    )


def format_test_results(results: List[Dict], sql: str = None):
    """Format test results using MCP UI components"""
    
    if not results:
        return Alert(
            variant="info",
            title="No Results",
            message="No test results found matching your query."
        )
    
    # Calculate aggregates
    total_tests = sum(r.get('tests_passed', 0) + r.get('tests_failed', 0) for r in results)
    total_passed = sum(r.get('tests_passed', 0) for r in results)
    total_failed = sum(r.get('tests_failed', 0) for r in results)
    total_skipped = sum(r.get('tests_skipped', 0) for r in results)
    pass_rate = round((total_passed / total_tests * 100) if total_tests > 0 else 0, 1)
    
    components = []
    
    # Warning for failures
    if total_failed > 0:
        components.append(
            Alert(
                variant="error",
                title="Test Failures Detected",
                message=f"Found {total_failed} failed test(s) across {len(results)} test run(s)."
            )
        )
    
    # SQL collapsible
    if sql:
        components.append(
            Collapsible(
                title="Generated SQL Query",
                collapsed=True,
                content=Code(
                    language="sql",
                    code=sql
                )
            )
        )
    
    # Statistics
    components.append(
        Stats(
            items=[
                {"label": "Test Runs", "value": str(len(results)), "variant": "default"},
                {"label": "Total Tests", "value": str(total_tests), "variant": "default"},
                {"label": "Passed", "value": str(total_passed), "variant": "success"},
                {"label": "Failed", "value": str(total_failed), "variant": "error"},
                {"label": "Skipped", "value": str(total_skipped), "variant": "warning"},
                {
                    "label": "Pass Rate",
                    "value": f"{pass_rate}%",
                    "variant": "success" if pass_rate >= 95 else "warning" if pass_rate >= 80 else "error"
                }
            ]
        )
    )
    
    # Build table
    headers = ["App", "Version", "Test Type", "Passed", "Failed", "Skipped", "Duration", "Date"]
    rows = []
    
    for r in results:
        date_str = str(r.get('date', 'N/A'))[:16] if r.get('date') else 'N/A'
        duration = r.get('test_duration_seconds', 0)
        duration_str = f"{duration}s" if duration else "N/A"
        
        has_failures = r.get('tests_failed', 0) > 0
        row_variant = "error" if has_failures else "success"
        
        rows.append({
            "cells": [
                r.get('app_name', 'N/A'),
                r.get('app_version', 'N/A'),
                r.get('test_type', 'N/A'),
                str(r.get('tests_passed', 0)),
                str(r.get('tests_failed', 0)),
                str(r.get('tests_skipped', 0)),
                duration_str,
                date_str
            ],
            "variant": row_variant
        })
    
    components.append(
        Table(
            title="Test Results",
            headers=headers,
            rows=rows,
            sortable=True,
            filterable=True
        )
    )
    
    return Container(
        layout="vertical",
        components=components
    )


def format_cache_stats(stats: Dict):
    """Format cache statistics using MCP UI components"""
    
    components = []
    
    # Summary stats
    components.append(
        Stats(
            items=[
                {"label": "Cached Queries", "value": str(stats.get('total_entries', 0)), "variant": "default"},
                {"label": "Total Cache Hits", "value": str(stats.get('total_hits', 0)), "variant": "success"},
                {"label": "Avg Uses/Query", "value": str(round(stats.get('avg_uses_per_query', 0), 1)), "variant": "default"},
                {"label": "Unique Users", "value": str(stats.get('unique_users', 0)), "variant": "default"}
            ]
        )
    )
    
    # Top queries table
    top_queries = stats.get('top_queries', [])
    if top_queries:
        headers = ["Query Pattern", "Uses", "Last Used"]
        rows = []
        
        for q in top_queries:
            last_used = str(q.get('last_used', 'N/A'))[:16]
            rows.append({
                "cells": [
                    q.get('cache_key', 'N/A'),
                    str(q.get('use_count', 0)),
                    last_used
                ]
            })
        
        components.append(
            Table(
                title="Most Popular Queries",
                headers=headers,
                rows=rows,
                sortable=True
            )
        )
    
    return Container(
        layout="vertical",
        components=components
    )


def determine_result_type(results: List[Dict]) -> str:
    """Determine if results are from deployment_data or test_data"""
    if not results:
        return "unknown"
    
    first_row = results[0]
    
    if 'deploy_result' in first_row:
        return "deployment"
    
    if 'test_type' in first_row or 'tests_passed' in first_row:
        return "test"
    
    return "unknown"


def format_generic_table(results: List[Dict], title: str = "Results"):
    """Generic table formatter for unknown result types"""
    if not results:
        return Alert(
            variant="info",
            title="No Results",
            message="No results found."
        )
    
    # Extract headers from first row
    headers = list(results[0].keys())
    
    # Build rows
    rows = []
    for r in results:
        rows.append({
            "cells": [str(r.get(h, 'N/A')) for h in headers]
        })
    
    return Table(
        title=title,
        headers=headers,
        rows=rows,
        sortable=True,
        filterable=True
    )


def register(mcp):
    
    @mcp.tool(
        name="query_cicd_prepare",
        description="""Prepare a CI/CD database query from natural language.

        This is the FIRST step for querying the CI/CD database. It will:
        - Extract query parameters (app name, environment, time range)
        - Check if this query pattern is already cached (fast!)
        - Return results with rich UI formatting if cached
        - Provide context for SQL generation if not cached

        Example queries:
        - "Show me deployments for frontend in the last week"
        - "How many tests ran for api-gateway today?"
        - "List failures in the last month"
        """
    )
    def query_cicd_prepare(question: str):
        """Phase 1: Prepare NL query for SQL generation or return cached results."""
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
            
            status = data.get("status")
            
            if status == "success":
                # Cache hit - format with UI
                results = data.get("results", [])
                sql = data.get("sql")
                
                # Determine result type and format accordingly
                result_type = determine_result_type(results)
                
                if result_type == "deployment":
                    ui_component = format_deployment_results(results, sql)
                elif result_type == "test":
                    ui_component = format_test_results(results, sql)
                else:
                    ui_component = format_generic_table(results)
                
                # Add cache success message
                if data.get("cached"):
                    cache_msg = Container(
                        layout="vertical",
                        components=[
                            Alert(
                                variant="success",
                                title="Cache Hit",
                                message=f"Results retrieved from cache. Query has been used {data.get('use_count', 'multiple')} times."
                            ),
                            ui_component
                        ]
                    )
                    return cache_msg
                
                return ui_component
            
            elif status == "needs_generation":
                # Cache miss - return context (no UI needed yet)
                return {
                    "status": "needs_generation",
                    "cached": False,
                    "slots": data.get("slots", {}),
                    "schema": data.get("schema", {}),
                    "cache_key": data.get("cache_key"),
                    "instruction": data.get("instruction"),
                    "message": "Please generate SQL using the provided schema and call query_cicd_execute"
                }
            
            elif status == "error":
                # Error - format as alert
                warnings = data.get("warnings", [])
                suggestions = data.get("suggestions", [])
                details = "\n".join(warnings + suggestions) if (warnings or suggestions) else None
                
                return Alert(
                    variant="error",
                    title="Query Error",
                    message=data.get("message", "Unknown error"),
                    details=details
                )
            
            else:
                return Alert(
                    variant="error",
                    title="Unexpected Response",
                    message=f"Unexpected status: {status}"
                )
        
        except requests.exceptions.Timeout:
            return Alert(
                variant="error",
                title="Timeout",
                message="CI/CD database query preparation timed out. Please try again."
            )
        except requests.exceptions.ConnectionError:
            return Alert(
                variant="error",
                title="Connection Error",
                message="Could not connect to CI/CD database service. Service may be down."
            )
        except Exception as e:
            return Alert(
                variant="error",
                title="Error",
                message=f"Error connecting to CI/CD database: {str(e)}"
            )
    
    
    @mcp.tool(
        name="query_cicd_execute",
        description="""Execute a generated SQL query against the CI/CD database.

        This is the SECOND step, ONLY used when query_cicd_prepare returns 
        status="needs_generation". Results are formatted with rich UI components.
        """
    )
    def query_cicd_execute(
        sql: str, 
        cache_key: str, 
        confirm_cache: bool = True
    ):
        """Phase 2: Execute generated SQL and optionally cache it."""
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
                results = data.get("results", [])
                sql_query = data.get("sql")
                
                # Format with UI
                result_type = determine_result_type(results)
                
                if result_type == "deployment":
                    ui_component = format_deployment_results(results, sql_query)
                elif result_type == "test":
                    ui_component = format_test_results(results, sql_query)
                else:
                    ui_component = format_generic_table(results)
                
                # Add success message if newly cached
                if data.get("cached"):
                    return Container(
                        layout="vertical",
                        components=[
                            Alert(
                                variant="success",
                                title="Query Cached",
                                message="This query has been cached for faster future access by all team members."
                            ),
                            ui_component
                        ]
                    )
                
                return ui_component
            
            elif status == "error":
                return Alert(
                    variant="error",
                    title="SQL Execution Error",
                    message=data.get("message", "SQL execution failed"),
                    details=f"Error Type: {data.get('error_type', 'Unknown')}\n\nSQL:\n{sql}"
                )
            
            else:
                return Alert(
                    variant="error",
                    title="Unexpected Response",
                    message=f"Unexpected status: {status}"
                )
        
        except requests.exceptions.Timeout:
            return Alert(
                variant="error",
                title="Timeout",
                message="SQL execution timed out. Query may be too complex."
            )
        except Exception as e:
            return Alert(
                variant="error",
                title="Execution Error",
                message=f"Error executing SQL: {str(e)}"
            )
    
    
    @mcp.tool(
        name="query_cicd_cache_stats",
        description="""Get statistics about cached CI/CD queries with rich formatting."""
    )
    def query_cicd_cache_stats():
        """Get cache statistics formatted with UI components."""
        try:
            resp = requests.get(
                f"{NL2SQL_PREPARE_URL.rsplit('/', 1)[0]}/cache/stats",
                timeout=NL2SQL_TIMEOUT
            )
            resp.raise_for_status()
            stats = resp.json()
            
            return format_cache_stats(stats)
        
        except Exception as e:
            return Alert(
                variant="error",
                title="Error",
                message=f"Failed to fetch cache stats: {str(e)}"
            )
    
    
    @mcp.tool(
        name="query_cicd_cache_list",
        description="""List cached CI/CD query patterns."""
    )
    def query_cicd_cache_list(limit: int = 50):
        """List cached query patterns."""
        try:
            resp = requests.get(
                f"{NL2SQL_PREPARE_URL.rsplit('/', 1)[0]}/cache/list",
                params={"limit": limit},
                timeout=NL2SQL_TIMEOUT
            )
            resp.raise_for_status()
            data = resp.json()
            
            cached_queries = data.get('cached_queries', [])
            
            if not cached_queries:
                return Alert(
                    variant="info",
                    title="No Cache Entries",
                    message="No queries have been cached yet."
                )
            
            headers = ["Cache Key", "Created At", "Last Used", "Use Count", "Created By"]
            rows = []
            
            for q in cached_queries:
                rows.append({
                    "cells": [
                        q.get('cache_key', 'N/A'),
                        str(q.get('created_at', 'N/A'))[:16],
                        str(q.get('last_used', 'N/A'))[:16],
                        str(q.get('use_count', 0)),
                        q.get('created_by', 'N/A')
                    ]
                })
            
            return Table(
                title=f"Cached Queries (showing {len(cached_queries)})",
                headers=headers,
                rows=rows,
                sortable=True,
                filterable=True
            )
        
        except Exception as e:
            return Alert(
                variant="error",
                title="Error",
                message=f"Failed to list cache: {str(e)}"
            )
