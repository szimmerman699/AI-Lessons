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

    @pytest.mark.asyncio
    async def test_validate_file_path_valid(self, sample_text_file: str) -> None:
        """Test validation of a valid existing file."""
        path = await validate_file_path(sample_text_file)
        assert path.exists()
        assert path.is_file()

    @pytest.mark.asyncio
    async def test_validate_file_path_not_found(self) -> None:
        """Test validation raises error for non-existent file."""
        with pytest.raises(DocumentNotFoundError):
            await validate_file_path("/nonexistent/path/file.txt")

    @pytest.mark.asyncio
    async def test_validate_file_path_is_directory(self, tmp_path) -> None:
        """Test validation raises error when path is a directory."""
        dir_path = tmp_path / "test_dir"
        dir_path.mkdir()

        with pytest.raises(InvalidDocumentError):
            await validate_file_path(str(dir_path))

    @pytest.mark.asyncio
    async def test_validate_file_path_with_spaces(self, tmp_path) -> None:
        """Test validation of file with spaces in name."""
        spaced_file = tmp_path / "my test document.txt"
        spaced_file.write_text("content")

        path = await validate_file_path(str(spaced_file))
        assert path.exists()
        assert "test document" in path.name

    @pytest.mark.asyncio
    async def test_validate_file_path_special_characters(self, tmp_path) -> None:
        """Test validation of file with special characters."""
        special_file = tmp_path / "doc-2024_v1.0.txt"
        special_file.write_text("content")

        path = await validate_file_path(str(special_file))
        assert path.exists()
        assert path.name == "doc-2024_v1.0.txt"

    @pytest.mark.asyncio
    async def test_validate_file_path_returns_path_object(
        self, sample_text_file: str
    ) -> None:
        """Test that validation returns a Path object."""
        result = await validate_file_path(sample_text_file)
        assert isinstance(result, Path)

    @pytest.mark.asyncio
    async def test_validate_file_path_relative_path(self, tmp_path) -> None:
        """Test validation of relative file path."""
        original_cwd = os.getcwd()
        try:
            file_in_dir = tmp_path / "relative_test.txt"
            file_in_dir.write_text("content")

            os.chdir(str(tmp_path))
            path = await validate_file_path("relative_test.txt")
            assert path.exists()
        finally:
            os.chdir(original_cwd)


class TestCheckFileSize:
    """Tests for file size validation."""

    @pytest.mark.asyncio
    async def test_check_file_size_within_limit(self, sample_text_file: str) -> None:
        """Test file within size limit passes validation."""
        path = Path(sample_text_file)
        await check_file_size(path)  # Should not raise

    @pytest.mark.asyncio
    async def test_check_file_size_exceeds_limit(self, large_text_file: str) -> None:
        """Test file exceeding size limit raises error."""
        path = Path(large_text_file)
        with pytest.raises(FileSizeExceededError):
            await check_file_size(path)


class TestExtractText:
    """Tests for text extraction."""

    @pytest.mark.asyncio
    async def test_extract_text_valid_file(self, sample_text_file: str) -> None:
        """Test successful text extraction from valid file."""
        content = await extract_text(sample_text_file)
        assert isinstance(content, str)
        assert len(content) > 0
        assert "quick brown fox" in content

    @pytest.mark.asyncio
    async def test_extract_text_not_found(self) -> None:
        """Test extraction from non-existent file raises error."""
        with pytest.raises(DocumentNotFoundError):
            await extract_text("/nonexistent/file.txt")

    @pytest.mark.asyncio
    async def test_extract_text_unsupported_format(self, tmp_path) -> None:
        """Test extraction from unsupported format raises error."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("fake pdf content")

        with pytest.raises(UnsupportedFormatError):
            await extract_text(str(pdf_file))

    @pytest.mark.asyncio
    async def test_extract_text_file_too_large(self, large_text_file: str) -> None:
        """Test extraction from oversized file raises error."""
        with pytest.raises(FileSizeExceededError):
            await extract_text(large_text_file)

    @pytest.mark.asyncio
    async def test_extract_text_empty_file(self, empty_text_file: str) -> None:
        """Test extraction from empty file succeeds."""
        content = await extract_text(empty_text_file)
        assert content == ""


class TestAnalyzeText:
    """Tests for text analysis."""

    @pytest.mark.asyncio
    async def test_analyze_text_valid_content(self) -> None:
        """Test analysis of valid text content."""
        content = "The quick brown fox jumps over the lazy dog."
        result = await analyze_text(content)

        assert result["word_count"] == 9
        assert result["char_count"] == len(content)
        assert result["line_count"] == 1
        assert isinstance(result["avg_word_length"], float)

    @pytest.mark.asyncio
    async def test_analyze_text_multiline_content(self) -> None:
        """Test analysis of multiline text."""
        content = "Line one\nLine two\nLine three"
        result = await analyze_text(content)

        assert result["word_count"] == 6
        assert result["line_count"] == 3

    @pytest.mark.asyncio
    async def test_analyze_text_empty_content(self) -> None:
        """Test analysis of empty content raises error."""
        with pytest.raises(InvalidDocumentError):
            await analyze_text("")

    @pytest.mark.asyncio
    async def test_analyze_text_whitespace_only(self) -> None:
        """Test analysis of whitespace-only content raises error."""
        with pytest.raises(InvalidDocumentError):
            await analyze_text("   \n\n   \t\t")

    @pytest.mark.asyncio
    async def test_analyze_text_word_frequency_basic(self) -> None:
        """Test word frequency counts words correctly."""
        content = "hello world hello"
        result = await analyze_text(content)

        assert result["word_frequency"]["hello"] == 2
        assert result["word_frequency"]["world"] == 1

    @pytest.mark.asyncio
    async def test_analyze_text_word_frequency_case_insensitive(self) -> None:
        """Test word frequency is case-insensitive."""
        content = "Hello HELLO hello"
        result = await analyze_text(content)

        assert result["word_frequency"]["hello"] == 3
        assert len(result["word_frequency"]) == 1

    @pytest.mark.asyncio
    async def test_analyze_text_word_frequency_excludes_punctuation(self) -> None:
        """Test word frequency excludes punctuation."""
        content = "Hello, world! Hello?"
        result = await analyze_text(content)

        assert result["word_frequency"]["hello"] == 2
        assert result["word_frequency"]["world"] == 1
        assert "hello," not in result["word_frequency"]
        assert "world!" not in result["word_frequency"]

    @pytest.mark.asyncio
    async def test_analyze_text_return_structure(self) -> None:
        """Test that analyze_text returns all required keys with correct types."""
        content = "The quick brown fox jumps over the lazy dog"
        result = await analyze_text(content)

        # Verify all required keys are present
        required_keys = {
            "word_count",
            "char_count",
            "line_count",
            "avg_word_length",
            "word_frequency",
        }
        assert set(result.keys()) == required_keys

        # Verify correct types
        assert isinstance(result["word_count"], int)
        assert isinstance(result["char_count"], int)
        assert isinstance(result["line_count"], int)
        assert isinstance(result["avg_word_length"], float)
        assert isinstance(result["word_frequency"], dict)

        # Verify word_frequency contains strings as keys and ints as values
        for key, value in result["word_frequency"].items():
            assert isinstance(key, str)
            assert isinstance(value, int)

    @pytest.mark.asyncio
    async def test_analyze_text_avg_word_length_calculation(self) -> None:
        """Test correct calculation of average word length."""
        # "hello world" = 11 chars (including space) / 2 words = 5.5
        content = "hello world"
        result = await analyze_text(content)

        assert result["avg_word_length"] == 5.5

    @pytest.mark.asyncio
    async def test_analyze_text_single_word(self) -> None:
        """Test analysis of a single word."""
        content = "hello"
        result = await analyze_text(content)

        assert result["word_count"] == 1
        assert result["char_count"] == 5
        assert result["line_count"] == 1
        assert result["avg_word_length"] == 5.0
        assert result["word_frequency"]["hello"] == 1

    @pytest.mark.asyncio
    async def test_analyze_text_with_numbers(self) -> None:
        """Test word frequency correctly handles numbers."""
        content = "test123 hello 456 world"
        result = await analyze_text(content)

        assert "test123" in result["word_frequency"]
        assert "456" in result["word_frequency"]
        assert result["word_count"] == 4


class TestReadCsvToData:
    """Tests for CSV file reading and data conversion."""

    @pytest.mark.asyncio
    async def test_read_csv_valid_data(self, tmp_path: Path) -> None:
        """Test CSV reading and structure conversion."""
        csv_file = tmp_path / "sample.csv"
        csv_file.write_text("name,age,city\nAlice,30,NYC\nBob,25,LA\n")

        result = await extract_text(str(csv_file))
        assert "Alice" in result
        assert "30" in result

    @pytest.mark.asyncio
    async def test_read_csv_empty_file(self, tmp_path: Path) -> None:
        """Test handling of empty CSV file."""
        empty_csv = tmp_path / "empty.csv"
        empty_csv.write_text("")

        with pytest.raises(InvalidDocumentError):
            await extract_text(str(empty_csv))

    @pytest.mark.asyncio
    async def test_read_csv_missing_file(self) -> None:
        """Test error handling for missing file."""
        with pytest.raises(DocumentNotFoundError):
            await extract_text("/nonexistent/file.csv")

    @pytest.mark.asyncio
    async def test_read_csv_unsupported_format(self, tmp_path: Path) -> None:
        """Test that CSV format is not yet supported."""
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("name,value\ntest,123\n")

        # CSV is not in SUPPORTED_MIME_TYPES yet
        with pytest.raises(UnsupportedFormatError):
            await extract_text(str(csv_file))


class TestProcessDocument:
    """Tests for end-to-end document processing."""

    @pytest.mark.asyncio
    async def test_process_document_valid(self, sample_text_file: str) -> None:
        """Test successful end-to-end document processing."""
        result = await process_document(sample_text_file)

        assert result["status"] == "success"
        assert result["file_path"] == sample_text_file
        assert "content" in result
        assert "analysis" in result
        assert isinstance(result["analysis"]["word_count"], int)

    @pytest.mark.asyncio
    async def test_process_document_not_found(self) -> None:
        """Test processing non-existent document raises error."""
        with pytest.raises(DocumentNotFoundError):
            await process_document("/nonexistent/doc.txt")

    @pytest.mark.asyncio
    async def test_process_document_invalid_format(self, tmp_path) -> None:
        """Test processing invalid format raises error."""
        doc_file = tmp_path / "test.docx"
        doc_file.write_text("fake docx")

        with pytest.raises(UnsupportedFormatError):
            await process_document(str(doc_file))

    @pytest.mark.asyncio
    async def test_process_document_empty_file(self, empty_text_file: str) -> None:
        """Test processing empty document raises error."""
        with pytest.raises(InvalidDocumentError):
            await process_document(empty_text_file)

    @pytest.mark.asyncio
    async def test_process_document_file_too_large(self, large_text_file: str) -> None:
        """Test processing oversized document raises error."""
        with pytest.raises(FileSizeExceededError):
            await process_document(large_text_file)
