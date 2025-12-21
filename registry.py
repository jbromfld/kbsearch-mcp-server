from tools import rag_search, cicd_db_query

def register_tools(mcp):
    rag_search.register(mcp)
    cicd_db_query.register(mcp)