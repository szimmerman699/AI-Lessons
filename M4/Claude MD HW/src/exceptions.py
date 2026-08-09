"""Custom exceptions for Document Analyzer."""


class DocumentError(Exception):
    """Base exception for document processing errors."""

    pass


class InvalidDocumentError(DocumentError):
    """Raised when document format or content is invalid."""

    pass


class DocumentNotFoundError(DocumentError):
    """Raised when document file cannot be found."""

    pass


class FileSizeExceededError(DocumentError):
    """Raised when document exceeds size limit (50MB)."""

    pass


class UnsupportedFormatError(DocumentError):
    """Raised when document format is not supported."""

    pass
