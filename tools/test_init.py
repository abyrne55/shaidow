# Generated-By: Claude 4.5 Sonnet

import pytest
import json
from unittest.mock import Mock
from tools import during_call_status_message, after_call_status_message, spinner
import llm


class TestDuringCallStatusMessage:
    """Tests for during_call_status_message function."""

    def test_registered_tool_with_template_substitution(self):
        """Test that registered tools substitute template variables correctly."""
        tool = Mock()
        tool.name = "KnowledgeBase_search"
        tool_call = Mock(arguments={"query": "disk pressure"})

        message = during_call_status_message(tool, tool_call)

        # Should substitute {query} in the template
        assert message == "Searching knowledgebase for 'disk pressure'..."

    def test_unregistered_tool_fallback(self):
        """Test fallback message for unregistered tool."""
        tool = Mock()
        tool.name = "UnknownTool_method"
        tool_call = Mock(arguments={"arg1": "value1"})

        message = during_call_status_message(tool, tool_call)

        # Should use fallback format
        assert "Using UnknownTool_method" in message
        assert "arg1" in message


class TestAfterCallStatusMessage:
    """Tests for after_call_status_message function."""

    def test_result_count_from_json_list(self):
        """Test that result count is extracted from JSON list results."""
        tool = Mock()
        tool.name = "KnowledgeBase_search"
        tool_call = Mock(arguments={"query": "disk pressure"})

        # Simulate JSON list result
        result_data = [
            {"id": "doc1", "relevance_score": 0.95, "content": "Article 1"},
            {"id": "doc2", "relevance_score": 0.92, "content": "Article 2"},
            {"id": "doc3", "relevance_score": 0.91, "content": "Article 3"}
        ]
        tool_result = Mock(output=json.dumps(result_data))

        message = after_call_status_message(tool, tool_call, tool_result)

        # Should count 3 results and substitute into template
        assert message == "Reading through 3 articles regarding 'disk pressure'..."

    def test_non_json_result_defaults_to_zero(self):
        """Test that non-JSON results default to result_count=0."""
        tool = Mock()
        tool.name = "KnowledgeBase_search"
        tool_call = Mock(arguments={"query": "test"})
        tool_result = Mock(output="Not a JSON response")

        message = after_call_status_message(tool, tool_call, tool_result)

        # Should handle gracefully with result_count=0
        assert "Reading through 0 articles regarding 'test'..." == message

    def test_unregistered_tool_fallback(self):
        """Test fallback after-call message for unregistered tool."""
        tool = Mock()
        tool.name = "UnknownTool_method"
        tool_call = Mock(arguments={"arg1": "value1"})
        tool_result = Mock(output="some result")

        message = after_call_status_message(tool, tool_call, tool_result)

        # Should use fallback format
        assert "Reviewing output of UnknownTool_method call" in message


class TestSpinner:
    """Tests for spinner function."""

    def test_registered_tool_returns_specific_spinner(self):
        """Test that registered tools return their configured spinner."""
        tool = Mock()
        tool.name = "Clock_local_time"
        assert spinner(tool) == "clock"

        tool.name = "Web_search"
        assert spinner(tool) == "earth"

    def test_unregistered_tool_returns_default(self):
        """Test that unregistered tools use default dots10 spinner."""
        tool = Mock()
        tool.name = "UnknownTool_method"
        assert spinner(tool) == "dots10"
