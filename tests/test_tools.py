"""Tests for the three tool executors."""

from pyagent import tools
from pyagent.tools import bash, read, write


async def test_read_returns_file_contents(tmp_path):
    (tmp_path / "a.txt").write_text("contents")
    assert await read(str(tmp_path / "a.txt")) == "contents"


async def test_read_missing_file_is_an_error_not_a_crash(tmp_path):
    result = await read(str(tmp_path / "missing.txt"))
    assert result.startswith("Error:")


async def test_write_creates_parent_directories(tmp_path):
    target = tmp_path / "deep" / "nested" / "file.txt"
    result = await write(str(target), "payload")
    assert target.read_text() == "payload"
    assert "Wrote" in result


async def test_bash_captures_stdout_and_exit_code():
    assert await bash("echo hello") == "hello"
    failure = await bash("echo oops >&2; exit 3")
    assert "oops" in failure
    assert "exit code 3" in failure


async def test_bash_truncates_huge_output():
    output = await bash("seq 1 20000")
    assert "truncated" in output
    assert len(output) < 40_000


async def test_bash_times_out(monkeypatch):
    monkeypatch.setattr(tools, "BASH_TIMEOUT_SECONDS", 0.1)
    assert "timed out" in await bash("sleep 5")
