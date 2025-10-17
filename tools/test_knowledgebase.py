# Generated-By: Claude 4.5 Sonnet

import pytest
from unittest.mock import Mock, MagicMock, patch
from tools.knowledgebase import KnowledgeBase
import llm
from sqlite_utils import Database


class TestKnowledgeBase:
    """Tests for the KnowledgeBase tool."""

    def test_init_with_default_database(self):
        """Test KnowledgeBase initialization with default database path."""
        with patch('tools.knowledgebase.Database') as mock_db, \
             patch('tools.knowledgebase.llm.Collection') as mock_collection, \
             patch('tools.knowledgebase.user_dir') as mock_user_dir:

            mock_user_dir.return_value = Mock(__truediv__=lambda self, x: f"/fake/path/{x}")

            kb = KnowledgeBase("test-collection")

            # Should use default embeddings.db path
            mock_db.assert_called_once()
            mock_collection.assert_called_once_with("test-collection", mock_db.return_value, create=False)

    def test_init_with_custom_database(self):
        """Test KnowledgeBase initialization with custom database path."""
        with patch('tools.knowledgebase.Database') as mock_db, \
             patch('tools.knowledgebase.llm.Collection') as mock_collection:

            kb = KnowledgeBase("test-collection", "/custom/path/db.sqlite")

            mock_db.assert_called_once_with("/custom/path/db.sqlite")
            mock_collection.assert_called_once_with("test-collection", mock_db.return_value, create=False)

    def test_search_basic(self):
        """Test basic search functionality."""
        with patch('tools.knowledgebase.Database') as mock_db, \
             patch('tools.knowledgebase.llm.Collection') as mock_collection:

            # Create mock results with score attributes (all within 0.04 of top score)
            mock_result1 = Mock(id="doc1", score=0.95, content="First document")
            mock_result2 = Mock(id="doc2", score=0.92, content="Second document")
            mock_result3 = Mock(id="doc3", score=0.91, content="Third document")

            mock_collection.return_value.similar.return_value = [
                mock_result1, mock_result2, mock_result3
            ]

            kb = KnowledgeBase("test-collection")
            results = kb.search("test query", max_results=5)

            # Should call similar with correct parameters
            mock_collection.return_value.similar.assert_called_once_with("test query", number=5)

            # Should return list of dicts with id, relevance_score, content
            assert len(results) == 3
            assert results[0] == {'id': 'doc1', 'relevance_score': 0.95, 'content': 'First document'}
            assert results[1] == {'id': 'doc2', 'relevance_score': 0.92, 'content': 'Second document'}
            assert results[2] == {'id': 'doc3', 'relevance_score': 0.91, 'content': 'Third document'}

    def test_search_filters_by_relevance_threshold(self):
        """Test that search filters results within 0.04 of top score."""
        with patch('tools.knowledgebase.Database') as mock_db, \
             patch('tools.knowledgebase.llm.Collection') as mock_collection:

            # Top score is 0.95, so only results >= 0.91 should be included
            mock_result1 = Mock(id="doc1", score=0.95, content="Very relevant")
            mock_result2 = Mock(id="doc2", score=0.93, content="Also relevant")
            mock_result3 = Mock(id="doc3", score=0.91, content="Borderline relevant")
            mock_result4 = Mock(id="doc4", score=0.90, content="Not relevant enough")

            mock_collection.return_value.similar.return_value = [
                mock_result1, mock_result2, mock_result3, mock_result4
            ]

            kb = KnowledgeBase("test-collection")
            results = kb.search("test query")

            # Should only return first 3 results (within 0.04 of 0.95)
            assert len(results) == 3
            assert results[0]['id'] == 'doc1'
            assert results[1]['id'] == 'doc2'
            assert results[2]['id'] == 'doc3'

    def test_read_id_success(self):
        """Test reading a document by ID."""
        with patch('tools.knowledgebase.Database') as mock_db, \
             patch('tools.knowledgebase.llm.Collection') as mock_collection:

            # Mock the database query
            mock_table = Mock()
            mock_table.rows_where.return_value = [
                {"id": "doc1", "content": "Document content here", "collection_id": 1}
            ]
            mock_db.return_value.__getitem__.return_value = mock_table

            # Mock collection id
            mock_collection.return_value.id = 1

            kb = KnowledgeBase("test-collection")
            content = kb.read_id("doc1")

            # Should query the database correctly
            mock_table.rows_where.assert_called_once_with(
                "collection_id = ? and id = ?", (1, "doc1")
            )

            assert content == "Document content here"
