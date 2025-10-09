from ddgs import DDGS



class WebSearch:
    """
    A simple web search tool
    """
    def __init__(self):
        """
        Initialize the WebSearch client.
        """
        self.ddgs = DDGS()

    def web_search(self, query: str, max_results: int = 5) -> list[dict]:
        """
        Search the web for content relevant to the query.
        
        Args:
            query: The search query string
            max_results: Maximum number of results to return (default: 5)
            
        Returns:
            A list of dictionaries containing search results with keys:
            - title: The page title
            - url: The page URL
            - snippet: A brief description/snippet from the page
        """
        try:
            results = self.ddgs.text(query, max_results=max_results)
            return [
                {
                    'title': result.get('title', ''),
                    'url': result.get('href', ''),
                    'snippet': result.get('body', '')
                }
                for result in results
            ]
        except Exception as e:
            return [{'error': f'Search failed: {str(e)}'}]

