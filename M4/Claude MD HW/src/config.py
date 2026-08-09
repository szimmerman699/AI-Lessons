"""Configuration management for Document Analyzer."""

from dataclasses import dataclass, field
from typing import Tuple


@dataclass
class Config:
    """Application configuration.

    Attributes:
        MAX_DOCUMENT_SIZE: Maximum allowed document size in bytes. Documents
            exceeding this limit raise FileSizeExceededError.
        SUPPORTED_FORMATS: File extensions accepted by read_document().
            Documents with other extensions raise UnsupportedFormatError.
    """

    MAX_DOCUMENT_SIZE: int = 50 * 1024 * 1024  # 50MB
    SUPPORTED_FORMATS: Tuple[str, ...] = field(default_factory=lambda: (".txt", ".md"))


def get_config() -> Config:
    """Get application configuration.

    Returns:
        Config object with application settings.
    """
    return Config()
