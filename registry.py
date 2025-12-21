from tools.rag_search import rag_search
from tools.cicd_db_query import cicd_db_query

def register_tools(server):
    server.add_tool(rag_search)
    server.add_tool(cicd_db_query)