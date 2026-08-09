"""Tests for the Document Readers module."""

from pathlib import Path

import pytest

from src.exceptions import (
    DocumentNotFoundError,
    FileSizeExceededError,
    InvalidDocumentError,
    UnsupportedFormatError,
)
from src.readers import read_document


class TestReadDocument:
    """Tests for document reading functionality."""

    def test_read_document_txt_file(self, sample_text_file: str) -> None:
        """Test reading a valid .txt file."""
        content = read_document(sample_text_file)
        assert isinstance(content, str)
        assert "quick brown fox" in content

    def test_read_document_md_file(self, sample_markdown_file: str) -> None:
        """Test reading a valid .md file."""
        content = read_document(sample_markdown_file)
        assert isinstance(content, str)
        assert "# Sample Document" in content

    def test_read_document_not_found(self) -> None:
        """Test reading non-existent file raises DocumentNotFoundError."""
        with pytest.raises(DocumentNotFoundError):
            read_document("/nonexistent/path/file.txt")

    def test_read_document_is_directory(self, tmp_path: Path) -> None:
        """Test reading a directory raises InvalidDocumentError."""
        dir_path = tmp_path / "test_dir"
        dir_path.mkdir()

        with pytest.raises(InvalidDocumentError):
            read_document(str(dir_path))

    def test_read_document_unsupported_format(self, tmp_path: Path) -> None:
        """Test reading unsupported format raises UnsupportedFormatError."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("fake pdf")

        with pytest.raises(UnsupportedFormatError):
            read_document(str(pdf_file))

    def test_read_document_csv_unsupported(self, tmp_path: Path) -> None:
        """Test reading CSV (unsupported) raises UnsupportedFormatError."""
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("name,value\ntest,123\n")

        with pytest.raises(UnsupportedFormatError):
            read_document(str(csv_file))

    def test_read_document_exceeds_size_limit(self, large_text_file: str) -> None:
        """Test reading oversized file raises FileSizeExceededError."""
        with pytest.raises(FileSizeExceededError):
            read_document(large_text_file)

    def test_read_document_empty_file(self, empty_text_file: str) -> None:
        """Test reading empty file returns empty string."""
        content = read_document(empty_text_file)
        assert content == ""

    def test_read_document_with_special_characters(self, tmp_path: Path) -> None:
        """Test reading file with special characters and unicode."""
        special_file = tmp_path / "special.txt"
        special_file.write_text(
            "Content with émojis 🎉 and spëcial chars!", encoding="utf-8"
        )

        content = read_document(str(special_file))
        assert "émojis" in content
        assert "spëcial" in content

    def test_read_document_bad_encoding(self, tmp_path: Path) -> None:
        """Test reading file with invalid UTF-8 raises InvalidDocumentError."""
        bad_file = tmp_path / "bad_encoding.txt"
        bad_file.write_bytes(b"Valid text \x80 invalid UTF-8")

        with pytest.raises(InvalidDocumentError):
            read_document(str(bad_file))
