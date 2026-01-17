import os
import requests
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

RAG_URL = os.getenv("RAG_SERVICE_URL", "http://localhost:8000/query")
RAG_TIMEOUT = int(os.getenv("RAG_TIMEOUT", "30"))


def register(mcp):
    @mcp.tool(
        name="search_knowledge_base",
        description="""⚠️ PRIMARY TOOL - Search the internal knowledge base for documentation.

        ⚠️⚠️⚠️ CRITICAL CONSTRAINT ⚠️⚠️⚠️
        - You MUST call this tool BEFORE answering ANY technical or factual question
        - The knowledge base contains: Python docs, Java docs, JavaScript docs, NPM docs, Maven docs, AKS docs, CI/CD guides, deployment documentation, and more
        - NEVER answer from general knowledge without checking the knowledge base first
        - If you answer without calling this tool, you risk giving wrong information

        📚 Knowledge Base Contains:
        - Programming Language Documentation: Python (ALL modules, types, functions), Java, JavaScript
        - Package Managers: NPM, Maven, pip
        - Cloud & Infrastructure: Azure (AKS), AWS, deployment guides
        - CI/CD: Continuous integration, continuous delivery, pipelines
        - Development Tools: Git, Docker, Kubernetes
        - Internal systems and processes

        🎯 ALWAYS Use This Tool For:
        - Programming questions (Python types, Java syntax, JavaScript APIs, etc.)
        - "What is X?" questions about ANY technical topic
        - "How do I..." questions about tools, frameworks, or systems
        - Questions about deployment, CI/CD, infrastructure
        - ANY question where documentation might exist

        Example queries that MUST use this tool:
        - "What is Mistral-3?" (could be a documented system/tool/model)
        - "Describe how authentication works in this system"
        - "How do I configure the deployment pipeline?"
        - "What is the recommended approach for error handling?"
        - "Explain the database migration process"
        - "Where can I find the API documentation?"
        - "What is the onboarding process for AKS deployment?"

        What it returns:
        - Retrieved document chunks with citations [1], [2], etc.
        - Source URLs and relevance scores for each chunk
        - Performance metrics (latency, chunks retrieved)

        How to use the results:
        - Read and synthesize information from the retrieved chunks to answer the user's question
        - MANDATORY: After your answer, copy the ENTIRE SOURCES section verbatim from the tool output, including all URLs
        - DO NOT summarize or paraphrase the sources - copy them exactly as provided with full URLs
        - Use inline citations [1], [2] in your answer that match the source numbers
        - ALWAYS preserve the Query ID line for potential feedback submission
        - If no relevant chunks are returned (num_chunks=0), explicitly state: "I couldn't find this in the internal knowledge base, so I'll answer from my general knowledge:" before providing your answer
        """
    )
    def search_knowledge_base(
        query: str,
        profile: Optional[str] = None,
        top_k: int = 5
    ) -> str:
        """Execute a semantic search and retrieve relevant document chunks from the knowledge base.

        Args:
            query: The question to ask
            profile: Optional profile name (default: "default"). Available profiles can be queried from the RAG service.
            top_k: Number of relevant chunks to retrieve (default: 5)

        Returns:
            Formatted string with:
            - Retrieved document chunks with citations [1], [2], etc.
            - Sources section with titles and relevance scores
            - Query ID for feedback submission
            - Performance metrics
        """
        try:
            request_data = {
                "query": query,
                "top_k": top_k,
                "retrieve_only": True,  # Let Copilot synthesize from chunks
                "profile": profile or "default"  # Use 'default' profile if not specified
            }

            resp = requests.post(
                RAG_URL,
                json=request_data,
                timeout=RAG_TIMEOUT
            )
            resp.raise_for_status()
            data = resp.json()

            # Format chunks for Copilot to synthesize
            chunks = data.get("chunks", [])

            # Create formatted text for Copilot with content and sources
            chunks_text = "\n\n".join([
                f"{chunk['citation']} {chunk['title']}\n"
                f"Content:\n{chunk['content']}"
                for chunk in chunks
            ])

            # Format sources separately for clear citation
            sources_list = "\n".join([
                f"{chunk['citation']} {chunk['title']}" +
                (f" - {chunk['url']}" if chunk.get('url') else "") +
                f" (relevance: {chunk['score']:.3f})"
                for chunk in chunks
            ])

            metrics = data.get("metrics", {})
            query_id = data.get("query_id", "")

            # Check if we got any chunks
            if not chunks:
                return "No relevant information found in the knowledge base for this query."

            # Build response with chunks, sources, and metadata
            response_parts = [
                "# Retrieved Information",
                "",
                chunks_text,
                "",
                "---",
                "# SOURCES",
                sources_list,
                "",
                f"Query ID: {query_id} (use this for feedback)",
                f"Retrieved {len(chunks)} chunks in {metrics.get('latency_ms', 0):.0f}ms"
            ]

            return "\n".join(response_parts)
        except requests.exceptions.Timeout:
            return f"ERROR: Knowledge base search timed out after {RAG_TIMEOUT}s. The RAG service is taking too long. Try a simpler query or check if the service is running."
        except requests.exceptions.ConnectionError:
            return "ERROR: Could not connect to RAG Testing Pipeline. Ensure the service is running with 'docker-compose up -d'."
        except requests.exceptions.HTTPError as e:
            error_detail = "Unknown error"
            try:
                error_data = e.response.json()
                error_detail = error_data.get("detail", str(error_data))
            except Exception:
                error_detail = e.response.text

            return f"ERROR: RAG service returned error ({e.response.status_code}): {error_detail}"
        except requests.exceptions.RequestException as e:
            return f"ERROR: Failed to search knowledge base: {str(e)}"

    @mcp.tool(
        name="submit_feedback",
        description="""Submit feedback on a RAG query response.

        When to use:
        - When the user provides a rating or feedback on a previous answer (e.g., "Rating 7", "Rate this 8/10", "Score: 5 - needs better sources")
        - Parse the user's natural language into score (0-10) and optional comment
        - Use the query_id from the most recent search_knowledge_base response

        Parameters:
        - query_id: The query_id from the search_knowledge_base response (shown in the Query ID line)
        - score: Rating from 0-10 extracted from user's feedback (0=terrible, 10=perfect)
        - comment: Any additional feedback text from the user

        Examples of user feedback to parse:
        - "Rating 7. Needs to add links" → score=7, comment="Needs to add links"
        - "Rate this 9/10" → score=9, comment=""
        - "Score: 3 - not relevant" → score=3, comment="not relevant"
        - "10 out of 10, perfect!" → score=10, comment="perfect!"

        Output:
        - Confirmation that feedback was recorded"""
    )
    def submit_feedback(
        query_id: str,
        score: int,
        comment: str = ""
    ) -> str:
        """Submit feedback on a query response.

        Args:
            query_id: The query ID from search_knowledge_base response
            score: Score from 0-10
            comment: Optional comment about the answer quality

        Returns:
            Confirmation message
        """
        try:
            resp = requests.post(
                f"{RAG_URL.replace('/query', '/feedback')}",
                json={
                    "query_id": query_id,
                    "score": score,
                    "comment": comment
                },
                timeout=RAG_TIMEOUT
            )
            resp.raise_for_status()

            return f"✓ Feedback submitted successfully: {score}/10 for query {query_id}"
        except requests.exceptions.ConnectionError:
            return "ERROR: Could not connect to RAG Testing Pipeline to submit feedback."
        except requests.exceptions.HTTPError as e:
            error_detail = "Unknown error"
            try:
                error_data = e.response.json()
                error_detail = error_data.get("detail", str(error_data))
            except Exception:
                error_detail = e.response.text

            return f"ERROR: Feedback submission failed ({e.response.status_code}): {error_detail}"
        except requests.exceptions.RequestException as e:
            return f"ERROR: Failed to submit feedback: {str(e)}"
