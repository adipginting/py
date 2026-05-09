"""Tests for ToolDefinition."""

from py_coding_agent.domain.tool_definition import ToolDefinition


def test_tool_definition_has_name_and_description() -> None:
    """A tool definition captures name, description, and parameter schema."""
    tool = ToolDefinition(
        name="read",
        description="Read a file from disk",
        parameters={"path": {"type": "string"}},
    )

    assert tool.name == "read"
    assert tool.description == "Read a file from disk"
    assert tool.parameters == {"path": {"type": "string"}}
