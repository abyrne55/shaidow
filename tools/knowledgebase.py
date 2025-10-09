import llm
from sqlite_utils import Database
from llm import user_dir


class KnowledgeBase:
    """
    A read-only wrapper around llm.Collection, for knowledge base searches. 
    """
    def __init__(self, collection_name: str, database_path: str = None):
        """
        Initialize the KnowledgeBase

        Raises llm.CollectionDoesNotExist if the collection does not exist
        
        Args:
            collection_name: Name of the collection
            database_path: Path to the SQLite database (optional; defaults to llm's default embeddings database)
        """
        self.database: Database = Database(database_path) if database_path else Database(user_dir() / "embeddings.db")
        self.collection: llm.Collection = llm.Collection(collection_name, self.database, create=False)

    def knowledgebase_search(self, query: str, max_results: int = 5) -> list[str]:
        """
        Search the knowledgebase for documents relevant to the query
        """
        all_results = sorted(self.collection.similar(query, number=max_results), key=lambda x: x.score, reverse=True)
        # Final results includes any results with a score that's within 0.04 of that of the most relevant result
        most_relevant_score = all_results[0].score
        relevant_results = [result for result in all_results if result.score >= most_relevant_score - 0.04]
        return list({'id':entry.id, 'relevance_score':entry.score, 'content':entry.content} for entry in relevant_results)