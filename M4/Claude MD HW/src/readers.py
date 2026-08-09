"""Document readers for loading files from disk."""

from pathlib import Path

from src.config import get_config
from src.exceptions import (
    DocumentNotFoundError,
    FileSizeExceededError,
    InvalidDocumentError,
    UnsupportedFormatError,
)
from src.logging_config import get_logger

logger = get_logger(__name__)


def read_document(file_path: str) -> str:
    """Read document content from disk.

    Supports .txt and .md formats. Validates file existence, format, and size
    against configured limits.

    Args:
        file_path: Path to the document file.

    Returns:
        Document content as string.

    Raises:
        DocumentNotFoundError: If file does not exist.
        InvalidDocumentError: If file is not readable or encoding is invalid.
        UnsupportedFormatError: If file format not in SUPPORTED_FORMATS.
        FileSizeExceededError: If file exceeds MAX_DOCUMENT_SIZE.
    """
    config = get_config()
    path = Path(file_path)

    if not path.exists():
        logger.error("document_not_found", path=file_path)
        raise DocumentNotFoundError(f"Document not found: {file_path}")

    if not path.is_file():
        logger.error("path_not_file", path=file_path)
        raise InvalidDocumentError(f"Path is not a file: {file_path}")

    file_ext = path.suffix.lower()
    if file_ext not in config.SUPPORTED_FORMATS:
        logger.error(
            "unsupported_format",
            path=file_path,
            extension=file_ext,
            supported=config.SUPPORTED_FORMATS,
        )
        raise UnsupportedFormatError(
            f"Unsupported format {file_ext}. Supported: {', '.join(config.SUPPORTED_FORMATS)}"
        )

    file_size = path.stat().st_size
    if file_size > config.MAX_DOCUMENT_SIZE:
        logger.error(
            "file_size_exceeded",
            path=file_path,
            size_bytes=file_size,
            limit_bytes=config.MAX_DOCUMENT_SIZE,
        )
        raise FileSizeExceededError(
            f"File exceeds size limit: {file_size} > {config.MAX_DOCUMENT_SIZE}"
        )

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError as exc:
        logger.error("invalid_encoding", path=file_path, error=str(exc))
        raise InvalidDocumentError(f"Failed to decode file: {exc}") from exc
    except Exception as exc:
        logger.error("read_failed", path=file_path, error=str(exc))
        raise InvalidDocumentError(f"Failed to read document: {exc}") from exc

    logger.info("document_read", path=file_path, size_bytes=file_size)
    return content
