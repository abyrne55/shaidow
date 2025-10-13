from this import d
from ddgs import DDGS
import trafilatura


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

    def read_url(self, url: str) -> str:
        """
        Fetch a web page and distill it to Markdown format.
        
        Args:
            url: The URL of the web page to fetch
            
        Returns:
            A Markdown-formatted string of the web page content
        """
        try:
            downloaded = trafilatura.fetch_url(url)
            if downloaded is None:
                raise RuntimeError(f"Could not fetch content from {url}")
            
            # Extract main content and convert to Markdown
            markdown_content = trafilatura.extract(
                downloaded,
                output_format='markdown',
                include_comments=False,
                include_tables=True,
                include_links=False,
                include_images=False,
                deduplicate=True
            )
            return markdown_content
            
        except Exception as e:
            return f"An error occurred: {str(e)}"

