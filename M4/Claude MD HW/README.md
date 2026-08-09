# Document Analyzer

A Python application for extracting, processing, and analyzing content from document files (PDF, DOCX, TXT).

## Setup

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

## Development

### Run Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test class
pytest tests/test_analyzer.py::TestExtractText -v

# Run single test
pytest tests/test_analyzer.py::TestExtractText::test_extract_text_valid_file -v
```

### Project Structure

- **src/analyzer.py** — Main module with document processing functions
- **src/exceptions.py** — Custom exception classes
- **src/logging_config.py** — Structured logging setup (structlog)
- **tests/conftest.py** — Pytest fixtures (sample files, fixtures)
- **tests/test_analyzer.py** — Test suite (24 tests across 6 classes)

## CLAUDE.md

This project includes **CLAUDE.md** with 10 specific, actionable rules that every Claude Code session will follow:

1. Type hints on all function signatures
2. Naming conventions (snake_case functions, PascalCase classes)
3. Import ordering (stdlib → third-party → local)
4. Logging with structlog (never print())
5. Specific exception handling
6. File handling with context managers
7. Pytest fixtures (not unittest)
8. Test file structure and organization
9. ≥85% coverage requirement
10. Secrets and environment management

See **constraints.md** for negative constraints that prevent agent overreach.

## Code Quality

- **Type checking:** Full type hints on all functions
- **Testing:** 24 tests with ≥85% coverage
- **Logging:** Structured logging via structlog
- **Error handling:** Specific exceptions, no bare Exception catches
- **Secrets:** Environment variables only, never hardcoded

## Example Usage

```python
from src.analyzer import process_document

# Process a document
result = process_document("sample.txt")

# View results
print(f"Status: {result['status']}")
print(f"Word count: {result['analysis']['word_count']}")
print(f"Character count: {result['analysis']['char_count']}")
```
