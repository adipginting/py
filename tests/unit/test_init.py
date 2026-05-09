"""Test that the package can be imported."""

import py_coding_agent


def test_can_import_domain() -> None:
    """The package must be importable and have a version."""
    assert py_coding_agent.__version__ == "0.1.0"
