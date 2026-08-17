"""Document analyzer - extract and process content from various document formats."""

import asyncio
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from src.config import get_config
from src.exceptions import (
    DocumentNotFoundError,
    FileSizeExceededError,
    InvalidDocumentError,
    UnsupportedFormatError,
)
from src.logging_config import get_logger

logger = get_logger(__name__)
SUPPORTED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "text/plain": ".txt",
}


async def validate_file_path(file_path: str) -> Path:
    """Validate that file exists and is readable.

    Args:
        file_path: Path to the document file.

    Returns:
        Path object if valid.

    Raises:
        DocumentNotFoundError: If file does not exist.
        InvalidDocumentError: If file is not readable.
    """
    def _check_path(fpath: str) -> Path:
        path = Path(fpath)
        if not path.exists():
            logger.error("file_not_found", path=fpath)
            raise DocumentNotFoundError(f"Document not found: {fpath}")
        if not path.is_file():
            logger.error("path_not_file", path=fpath)
            raise InvalidDocumentError(f"Path is not a file: {fpath}")
        if not os.access(path, os.R_OK):
            logger.error("file_not_readable", path=fpath)
            raise InvalidDocumentError(f"File not readable: {fpath}")
        return path

    return await asyncio.to_thread(_check_path, file_path)


async def check_file_size(file_path: Path) -> None:
    """Validate file does not exceed size limit.

    Args:
        file_path: Path to the document file.

    Raises:
        FileSizeExceededError: If file exceeds configured size limit.
    """
    def _stat_file(fpath: Path) -> int:
        return fpath.stat().st_size

    config = get_config()
    file_size = await asyncio.to_thread(_stat_file, file_path)

    if file_size > config.MAX_DOCUMENT_SIZE:
        logger.error(
            "file_size_exceeded",
            path=str(file_path),
            size_bytes=file_size,
            limit_bytes=config.MAX_DOCUMENT_SIZE,
        )
        raise FileSizeExceededError(
            f"File exceeds size limit: {file_size} > {config.MAX_DOCUMENT_SIZE}"
        )


async def extract_text(file_path: str) -> str:
    """Extract text content from a document.

    Currently supports: .txt files (PDF and DOCX support can be added).

    Args:
        file_path: Path to the document file.

    Returns:
        Extracted text content.

    Raises:
        DocumentNotFoundError: If file does not exist.
        FileSizeExceededError: If file exceeds size limit.
        InvalidDocumentError: If file format not supported or content invalid.
    """
    path = await validate_file_path(file_path)
    await check_file_size(path)

    file_ext = path.suffix.lower()

    if file_ext != ".txt":
        logger.error("unsupported_format", path=str(path), extension=file_ext)
        raise UnsupportedFormatError(
            f"Unsupported file format: {file_ext}. Supported: .txt, .pdf, .docx"
        )

    def _read_file(fpath: Path) -> str:
        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception as exc:
            logger.error("extraction_failed", path=str(fpath), error=str(exc))
            raise InvalidDocumentError(f"Failed to extract text: {exc}") from exc

    content = await asyncio.to_thread(_read_file, path)
    logger.info("text_extracted", path=str(path), length=len(content))
    return content


async def analyze_text(content: str) -> Dict[str, Any]:
    """Analyze extracted text and return metadata.

    Args:
        content: Text content to analyze.

    Returns:
        Dictionary with analysis results (word count, char count, word_frequency, etc.).

    Raises:
        InvalidDocumentError: If content is empty.
    """
    if not content or not content.strip():
        logger.warning("empty_content", content_length=len(content))
        raise InvalidDocumentError("Content is empty")

    word_count = len(content.split())
    char_count = len(content)
    line_count = len(content.split("\n"))

    words = re.findall(r"\w+", content.lower())
    word_frequency: Dict[str, int] = {}
    for word in words:
        word_frequency[word] = word_frequency.get(word, 0) + 1

    result = {
        "word_count": word_count,
        "char_count": char_count,
        "line_count": line_count,
        "avg_word_length": round(char_count / word_count, 2) if word_count > 0 else 0,
        "word_frequency": word_frequency,
    }

    logger.info(
        "text_analyzed",
        word_count=word_count,
        char_count=char_count,
        line_count=line_count,
        avg_word_length=result["avg_word_length"],
        unique_words=len(word_frequency),
    )
    return result


async def process_document(file_path: str) -> Dict[str, Any]:
    """Process a document end-to-end: validate, extract, analyze.

    Args:
        file_path: Path to the document file.

    Returns:
        Dictionary with extraction and analysis results.

    Raises:
        DocumentNotFoundError: If file does not exist.
        FileSizeExceededError: If file exceeds size limit.
        InvalidDocumentError: If file format or content invalid.
    """
    logger.info("processing_document", path=file_path)

    content = await extract_text(file_path)
    analysis = await analyze_text(content)

    result = {
        "file_path": file_path,
        "status": "success",
        "content": content,
        "analysis": analysis,
    }

    logger.info("document_processed", path=file_path, status="success")
    return result
