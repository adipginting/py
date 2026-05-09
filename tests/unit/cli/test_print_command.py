"""Tests for CLI print command."""

from click.testing import CliRunner

from py_coding_agent.cli.main import app


def test_print_command_outputs_assistant_response() -> None:
    """The print command runs once and prints the assistant response."""
    runner = CliRunner()
    result = runner.invoke(app, ["print", "Hello, world"])

    assert result.exit_code == 0
    assert "Echo: Hello, world" in result.output
