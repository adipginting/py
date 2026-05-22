"""Tests for CLI print command."""

from click.testing import CliRunner

from py_coding_agent.cli.main import app


def test_print_command_outputs_assistant_response() -> None:
    """The print command runs once and prints the assistant response."""
    runner = CliRunner()
    result = runner.invoke(app, ["print", "Hello, world"])

    assert result.exit_code == 0
    assert "Echo: Hello, world" in result.output


def test_print_command_with_echo_provider_flag() -> None:
    """The --provider echo flag forces the echo provider."""
    runner = CliRunner()
    result = runner.invoke(app, ["print", "--provider", "echo", "Test"])

    assert result.exit_code == 0
    assert "Echo: Test" in result.output


def test_print_command_errors_without_api_key_for_openai() -> None:
    """Selecting openai without OPENAI_API_KEY raises an error."""
    runner = CliRunner(env={"OPENAI_API_KEY": ""})
    result = runner.invoke(app, ["print", "--provider", "openai", "Test"])

    assert result.exit_code != 0
    assert "OPENAI_API_KEY" in result.output
