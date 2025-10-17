# Generated-By: Claude 4.5 Sonnet

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock
from shaidow import Command, build_prompt, extract_code_blocks_from_markdown, flatten_markdown_tokens
from rich.markdown import Markdown


class TestCommand:
    """Tests for the Command class."""

    def test_init(self):
        """Test Command initialization."""
        timestamp = datetime.now()
        cmd = Command("123", "echo hello", "hello\n", timestamp)

        assert cmd.id == "123"
        assert cmd.command == "echo hello"
        assert cmd.output == "hello\n"
        assert cmd.return_timestamp == timestamp

    def test_from_json_complete(self):
        """Test parsing complete JSON with all fields."""
        json_str = json.dumps({
            "id": "42",
            "command": "ls -la",
            "output": "total 0\n",
            "return_timestamp": "2025-01-15T10:30:45.123456Z"
        })

        cmd = Command.from_json(json_str)

        assert cmd.id == "42"
        assert cmd.command == "ls -la"
        assert cmd.output == "total 0\n"
        assert cmd.return_timestamp.year == 2025
        assert cmd.return_timestamp.month == 1
        assert cmd.return_timestamp.day == 15
        assert cmd.return_timestamp.hour == 10
        assert cmd.return_timestamp.minute == 30
        assert cmd.return_timestamp.second == 45

    def test_from_json_missing_timestamp(self):
        """Test parsing JSON without timestamp."""
        json_str = json.dumps({
            "id": "1",
            "command": "pwd",
            "output": "/home/user\n"
        })

        cmd = Command.from_json(json_str)

        assert cmd.id == "1"
        assert cmd.command == "pwd"
        assert cmd.output == "/home/user\n"
        assert cmd.return_timestamp is None

    def test_from_json_with_plus_offset(self):
        """Test parsing timestamp with +00:00 format."""
        json_str = json.dumps({
            "id": "1",
            "command": "date",
            "output": "Wed Jan 15\n",
            "return_timestamp": "2025-01-15T10:30:45+00:00"
        })

        cmd = Command.from_json(json_str)
        assert cmd.return_timestamp is not None

    def test_from_json_missing_required_field(self):
        """Test parsing JSON with missing fields (should handle gracefully)."""
        json_str = json.dumps({
            "id": "1"
            # Missing command, output
        })

        cmd = Command.from_json(json_str)

        assert cmd.id == "1"
        assert cmd.command is None
        assert cmd.output is None


class TestBuildPrompt:
    """Tests for the build_prompt function."""

    def test_build_prompt_regular_command(self):
        """Test building prompt for a regular command."""
        timestamp = datetime(2025, 1, 15, 10, 30, 45)
        cmd = Command("1", "echo test", "test\n", timestamp)

        prompt = build_prompt(cmd)

        assert "echo test" in prompt
        assert "test\n" in prompt
        assert "2025-01-15T10:30:45" in prompt
        assert "```sh" in prompt
        assert "```" in prompt

    def test_build_prompt_shell_comment(self):
        """Test that shell comments are forwarded directly."""
        timestamp = datetime.now()
        cmd = Command("1", "# What is this error?", "", timestamp)

        prompt = build_prompt(cmd)

        # Should return command as-is for comments
        assert prompt == "# What is this error?"
        assert "```sh" not in prompt


class TestExtractCodeBlocksFromMarkdown:
    """Tests for the extract_code_blocks_from_markdown function."""

    def test_extract_single_code_block(self):
        """Test extracting a single code block."""
        markdown_text = """
Here's what you should run:

```
oc get pods
```

That will show you the pods.
"""
        md = Markdown(markdown_text)
        blocks = extract_code_blocks_from_markdown(md)

        assert len(blocks) == 1
        assert blocks[0] == "oc get pods"

    def test_extract_multiple_code_blocks(self):
        """Test extracting multiple code blocks."""
        markdown_text = """
Try these commands:

```
kubectl get nodes
```

Then run:

```
kubectl describe node xyz
```
"""
        md = Markdown(markdown_text)
        blocks = extract_code_blocks_from_markdown(md)

        assert len(blocks) == 2
        assert blocks[0] == "kubectl get nodes"
        assert blocks[1] == "kubectl describe node xyz"

    def test_extract_no_code_blocks(self):
        """Test markdown with no code blocks."""
        markdown_text = "This is just plain text with no code."
        md = Markdown(markdown_text)
        blocks = extract_code_blocks_from_markdown(md)

        assert len(blocks) == 0

    def test_extract_ignores_inline_code(self):
        """Test that inline code is not extracted."""
        markdown_text = "Run the `ls` command to see files."
        md = Markdown(markdown_text)
        blocks = extract_code_blocks_from_markdown(md)

        # Inline code should not be extracted
        assert len(blocks) == 0


class TestFlattenMarkdownTokens:
    """Tests for the flatten_markdown_tokens function."""

    def test_flatten_simple_tokens(self):
        """Test flattening a simple token stream."""
        # Create mock tokens
        token1 = Mock(type="text", tag="p", children=None)
        token2 = Mock(type="fence", tag="code", children=None, content="test")

        tokens = [token1, token2]
        result = list(flatten_markdown_tokens(tokens))

        assert len(result) == 2
        assert result[0] == token1
        assert result[1] == token2

    def test_flatten_nested_tokens(self):
        """Test flattening nested tokens."""
        # Create nested structure
        child1 = Mock(type="text", tag="span", children=None)
        child2 = Mock(type="text", tag="strong", children=None)
        parent = Mock(type="paragraph", tag="p", children=[child1, child2])

        tokens = [parent]
        result = list(flatten_markdown_tokens(tokens))

        # Should flatten to just the children
        assert len(result) == 2
        assert result[0] == child1
        assert result[1] == child2

    def test_flatten_fence_not_recursed(self):
        """Test that fence tokens are not recursed into."""
        # Fence with fake children (should be ignored)
        child = Mock(type="text", tag="span", children=None)
        fence = Mock(type="fence", tag="code", children=[child], content="code")

        tokens = [fence]
        result = list(flatten_markdown_tokens(tokens))

        # Should return just the fence, not children
        assert len(result) == 1
        assert result[0] == fence

    def test_flatten_image_not_recursed(self):
        """Test that image tokens are not recursed into."""
        child = Mock(type="text", tag="span", children=None)
        image = Mock(type="image", tag="img", children=[child])

        tokens = [image]
        result = list(flatten_markdown_tokens(tokens))

        # Should return just the image, not children
        assert len(result) == 1
        assert result[0] == image
