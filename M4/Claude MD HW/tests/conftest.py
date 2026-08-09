"""Pytest configuration and shared fixtures for Document Analyzer tests."""

import pytest


@pytest.fixture
def sample_text_file(tmp_path):
    """Create a temporary text file with sample content.

    Args:
        tmp_path: Pytest's temporary directory fixture.

    Returns:
        Path to the temporary file as a string.
    """
    text_file = tmp_path / "sample.txt"
    content = "The quick brown fox jumps over the lazy dog.\nThis is a test document."
    text_file.write_text(content, encoding="utf-8")
    return str(text_file)


@pytest.fixture
def empty_text_file(tmp_path):
    """Create an empty temporary text file.

    Args:
        tmp_path: Pytest's temporary directory fixture.

    Returns:
        Path to the empty file as a string.
    """
    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("", encoding="utf-8")
    return str(empty_file)


@pytest.fixture
def large_text_file(tmp_path):
    """Create a large temporary text file (for testing size limits).

    Args:
        tmp_path: Pytest's temporary directory fixture.

    Returns:
        Path to the large file as a string.
    """
    large_file = tmp_path / "large.txt"
    # Create a file with 60MB of content (exceeds 50MB limit)
    large_content = "x" * (60 * 1024 * 1024)
    large_file.write_text(large_content, encoding="utf-8")
    return str(large_file)


@pytest.fixture
def whitespace_only_file(tmp_path):
    """Create a file with only whitespace.

    Args:
        tmp_path: Pytest's temporary directory fixture.

    Returns:
        Path to the whitespace file as a string.
    """
    ws_file = tmp_path / "whitespace.txt"
    ws_file.write_text("   \n\n   \t\t   ", encoding="utf-8")
    return str(ws_file)
