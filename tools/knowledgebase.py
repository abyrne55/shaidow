import llm

def search(query: str) -> list[str]:
    """
    Search the knowledgebase for documents relevant to the query
    """
    return [
        "This is a test response from the knowledgebase about the query: " + query, 
        "This is less relevant response from the knowledgebase about the query: " + query,
        "This is a third response from the knowledgebase about the query: " + query
    ]