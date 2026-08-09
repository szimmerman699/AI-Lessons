"""Tests for the Document Analyzer module."""

import os
from pathlib import Path

import pytest

from src.analyzer import (
    analyze_text,
    check_file_size,
    extract_text,
    process_document,
    validate_file_path,
)
from src.exceptions import (
    DocumentNotFoundError,
    FileSizeExceededError,
    InvalidDocumentError,
    UnsupportedFormatError,
)


class TestValidateFilePath:
    """Tests for file path validation."""

    def test_validate_file_path_valid(self, sample_text_file: str) -> None:
        """Test validation of a valid existing file."""
        path = validate_file_path(sample_text_file)
        assert path.exists()
        assert path.is_file()

    def test_validate_file_path_not_found(self) -> None:
        """Test validation raises error for non-existent file."""
        with pytest.raises(DocumentNotFoundError):
            validate_file_path("/nonexistent/path/file.txt")

    def test_validate_file_path_is_directory(self, tmp_path) -> None:
        """Test validation raises error when path is a directory."""
        dir_path = tmp_path / "test_dir"
        dir_path.mkdir()

        with pytest.raises(InvalidDocumentError):
            validate_file_path(str(dir_path))

    def test_validate_file_path_with_spaces(self, tmp_path) -> None:
        """Test validation of file with spaces in name."""
        spaced_file = tmp_path / "my test document.txt"
        spaced_file.write_text("content")

        path = validate_file_path(str(spaced_file))
        assert path.exists()
        assert "test document" in path.name

    def test_validate_file_path_special_characters(self, tmp_path) -> None:
        """Test validation of file with special characters."""
        special_file = tmp_path / "doc-2024_v1.0.txt"
        special_file.write_text("content")

        path = validate_file_path(str(special_file))
        assert path.exists()
        assert path.name == "doc-2024_v1.0.txt"

    def test_validate_file_path_returns_path_object(
        self, sample_text_file: str
    ) -> None:
        """Test that validation returns a Path object."""
        result = validate_file_path(sample_text_file)
        assert isinstance(result, Path)

    def test_validate_file_path_relative_path(self, tmp_path) -> None:
        """Test validation of relative file path."""
        original_cwd = os.getcwd()
        try:
            file_in_dir = tmp_path / "relative_test.txt"
            file_in_dir.write_text("content")

            os.chdir(str(tmp_path))
            path = validate_file_path("relative_test.txt")
            assert path.exists()
        finally:
            os.chdir(original_cwd)


class TestCheckFileSize:
    """Tests for file size validation."""

    def test_check_file_size_within_limit(self, sample_text_file: str) -> None:
        """Test file within size limit passes validation."""
        from pathlib import Path

        path = Path(sample_text_file)
        check_file_size(path)  # Should not raise

    def test_check_file_size_exceeds_limit(self, large_text_file: str) -> None:
        """Test file exceeding size limit raises error."""
        from pathlib import Path

        path = Path(large_text_file)
        with pytest.raises(FileSizeExceededError):
            check_file_size(path)


class TestExtractText:
    """Tests for text extraction."""

    def test_extract_text_valid_file(self, sample_text_file: str) -> None:
        """Test successful text extraction from valid file."""
        content = extract_text(sample_text_file)
        assert isinstance(content, str)
        assert len(content) > 0
        assert "quick brown fox" in content

    def test_extract_text_not_found(self) -> None:
        """Test extraction from non-existent file raises error."""
        with pytest.raises(DocumentNotFoundError):
            extract_text("/nonexistent/file.txt")

    def test_extract_text_unsupported_format(self, tmp_path) -> None:
        """Test extraction from unsupported format raises error."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("fake pdf content")

        with pytest.raises(UnsupportedFormatError):
            extract_text(str(pdf_file))

    def test_extract_text_file_too_large(self, large_text_file: str) -> None:
        """Test extraction from oversized file raises error."""
        with pytest.raises(FileSizeExceededError):
            extract_text(large_text_file)

    def test_extract_text_empty_file(self, empty_text_file: str) -> None:
        """Test extraction from empty file succeeds."""
        content = extract_text(empty_text_file)
        assert content == ""


class TestAnalyzeText:
    """Tests for text analysis."""

    def test_analyze_text_valid_content(self) -> None:
        """Test analysis of valid text content."""
        content = "The quick brown fox jumps over the lazy dog."
        result = analyze_text(content)

        assert result["word_count"] == 9
        assert result["char_count"] == len(content)
        assert result["line_count"] == 1
        assert isinstance(result["avg_word_length"], float)

    def test_analyze_text_multiline_content(self) -> None:
        """Test analysis of multiline text."""
        content = "Line one\nLine two\nLine three"
        result = analyze_text(content)

        assert result["word_count"] == 6
        assert result["line_count"] == 3

    def test_analyze_text_empty_content(self) -> None:
        """Test analysis of empty content raises error."""
        with pytest.raises(InvalidDocumentError):
            analyze_text("")

    def test_analyze_text_whitespace_only(self) -> None:
        """Test analysis of whitespace-only content raises error."""
        with pytest.raises(InvalidDocumentError):
            analyze_text("   \n\n   \t\t")


class TestReadCsvToData:
    """Tests for CSV file reading and data conversion."""

    def test_read_csv_valid_data(self, tmp_path: Path) -> None:
        """Test CSV reading and structure conversion."""
        csv_file = tmp_path / "sample.csv"
        csv_file.write_text("name,age,city\nAlice,30,NYC\nBob,25,LA\n")

        result = extract_text(str(csv_file))
        assert "Alice" in result
        assert "30" in result

    def test_read_csv_empty_file(self, tmp_path: Path) -> None:
        """Test handling of empty CSV file."""
        empty_csv = tmp_path / "empty.csv"
        empty_csv.write_text("")

        with pytest.raises(InvalidDocumentError):
            extract_text(str(empty_csv))

    def test_read_csv_missing_file(self) -> None:
        """Test error handling for missing file."""
        with pytest.raises(DocumentNotFoundError):
            extract_text("/nonexistent/file.csv")

    def test_read_csv_unsupported_format(self, tmp_path: Path) -> None:
        """Test that CSV format is not yet supported."""
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("name,value\ntest,123\n")

        # CSV is not in SUPPORTED_MIME_TYPES yet
        with pytest.raises(UnsupportedFormatError):
            extract_text(str(csv_file))


class TestProcessDocument:
    """Tests for end-to-end document processing."""

    def test_process_document_valid(self, sample_text_file: str) -> None:
        """Test successful end-to-end document processing."""
        result = process_document(sample_text_file)

        assert result["status"] == "success"
        assert result["file_path"] == sample_text_file
        assert "content" in result
        assert "analysis" in result
        assert isinstance(result["analysis"]["word_count"], int)

    def test_process_document_not_found(self) -> None:
        """Test processing non-existent document raises error."""
        with pytest.raises(DocumentNotFoundError):
            process_document("/nonexistent/doc.txt")

    def test_process_document_invalid_format(self, tmp_path) -> None:
        """Test processing invalid format raises error."""
        doc_file = tmp_path / "test.docx"
        doc_file.write_text("fake docx")

        with pytest.raises(UnsupportedFormatError):
            process_document(str(doc_file))

    def test_process_document_empty_file(self, empty_text_file: str) -> None:
        """Test processing empty document raises error."""
        with pytest.raises(InvalidDocumentError):
            process_document(empty_text_file)

    def test_process_document_file_too_large(self, large_text_file: str) -> None:
        """Test processing oversized document raises error."""
        with pytest.raises(FileSizeExceededError):
            process_document(large_text_file)
