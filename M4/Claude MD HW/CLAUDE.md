# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Document Analyzer is a Python application that extracts, processes, and analyzes content from various document formats (PDF, DOCX, TXT). It provides structured output for downstream processing and integrates with external APIs for language analysis. Used by internal teams for bulk document classification and content extraction.

## Stack

- Python 3.11+
- pytest for testing (not unittest)
- python-docx, PyPDF2 for document parsing
- structlog for structured logging
- pydantic for data validation
- python-dotenv for environment configuration

## Coding Conventions

- **Type hints required:** All function signatures must include full type hints, including return types. Use `from typing import Optional, List, Dict` for complex types.
- **Naming:** Use `snake_case` for functions and variables, `PascalCase` for classes. Private functions/attributes use `_leading_underscore`.
- **Import ordering:** All imports at the top of the file, never inside functions or classes. Order: stdlib → third-party → local, separated by blank lines. Alphabetize within each group. Example: `import os; from pathlib import Path;` (stdlib), then blank line, then `import pytest;` (third-party), then blank line, then `from src.analyzer import validate_file_path;` (local).
- **Logging:** Use `structlog.get_logger()` to instantiate loggers. Never use `print()` for logging or debugging. Configure in `src/logging_config.py`.
- **Exceptions:** Raise specific exceptions (ValueError, FileNotFoundError, NotImplementedError). Never catch bare `Exception`. Define custom exceptions in `src/exceptions.py` and re-raise with context.
- **File handling:** Always use context managers (`with` statement). Validate file paths before opening. Never assume file encoding—use UTF-8 with error handling.

## Testing

- **Framework:** pytest only. Do not use unittest.TestCase, setUp/tearDown methods, or unittest.mock. Use pytest fixtures instead.
- **File structure:** Tests live in `tests/` directory with `test_` prefix matching the module name (e.g., `test_analyzer.py` for `src/analyzer.py`).
- **Fixtures:** Define reusable fixtures in `tests/conftest.py`. Use `tmp_path` fixture for temporary files—do NOT create/cleanup files manually in test functions. Mock external API calls with `pytest-mock` or `unittest.mock.patch`. Every test that needs setup data (files, database records, mock objects) must use a fixture parameter, never inline setup code.
- **Coverage:** Aim for ≥85% coverage on all public functions. Run `pytest --cov=src tests/` to verify. Test error paths, not just happy paths.

## Production Constraints

- **Deployment:** Docker container deployed to AWS ECS. Environment variables injected at runtime.
- **Secrets management:** Never hardcode API keys, tokens, or credentials. Load from environment variables via `python-dotenv`. Never commit `.env` files—use `.env.example` as template.
- **API integrations:** All external API calls must have timeout (30s default), retry logic (3 attempts), and explicit error handling. Log failures with request/response data (no sensitive values).
- **File uploads:** Limit document file size to 50MB. Validate MIME types against whitelist (application/pdf, application/vnd.openxmlformats-officedocument.wordprocessingml.document, text/plain). Scan for malicious content before processing.
- **Logging in production:** Use structured logging (structlog). Include request IDs and correlation IDs for traceability. Never log PII (personal identifiable information) or sensitive document content.

## Read These Files

- @constraints.md

---

## Rule-Update Log

### Update 1: Import Ordering Clarification

**What mistake Claude made:**
When writing tests, Claude imported `Path` and `os` inside function bodies instead of at the top of the file:
```python
def test_validate_file_path_returns_path_object(...):
    from pathlib import Path  # ❌ Wrong
    result = validate_text(sample_file)
    assert isinstance(result, Path)
```

**What rule was missing or insufficient:**
Original rule: "Import ordering: stdlib → third-party → local, separated by blank lines. Alphabetize within each group."
- **Problem:** Rule specified the ORDER of imports but didn't explicitly forbid inline imports inside functions or classes.
- **Result:** Claude interpreted the rule as only requiring correct ordering, not location.

**What was added:**
Updated the import rule to be explicit:
> "All imports at the top of the file, never inside functions or classes. Order: stdlib → third-party → local, separated by blank lines. Alphabetize within each group. Example: `import os; from pathlib import Path;` (stdlib), then blank line, then `import pytest;` (third-party), then blank line, then `from src.analyzer import validate_file_path;` (local)."

**How the fix was verified:**
1. Rewrote the existing tests to move all imports to the top of the file (lines 3-19)
2. Removed inline imports from test functions (`test_validate_file_path_returns_path_object`, `test_validate_file_path_relative_path`)
3. Made the same request again: "Write a test for CSV data reading"
4. Claude correctly placed all new imports at the top of the file without any inline imports
5. Verified with `python -m py_compile tests/test_analyzer.py` — all code compiles

**Learning:** Vague rules lead to vague implementation. Future rules now include explicit examples and boundary cases.
