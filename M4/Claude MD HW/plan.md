# Plan: File Input Reader Module

## Context

The Document Analyzer currently hardcodes its size limit (`MAX_FILE_SIZE` in `src/analyzer.py`) and only reads `.txt` files inline inside `extract_text()`. There is no dedicated reader module and no central config. This plan adds a `src/config.py` (central config via `get_config()`) and a `src/readers.py` (`read_document()`) so file-loading and size/format validation live in one place, and `.md` support is added alongside `.txt`. Scope is intentionally narrow: no PDF/DOCX, no batch/directory scanning, no CLI, no caching — those are separate future features.

## Files to Modify/Create

### 1. `src/config.py` (new)
- `get_config()` returning a config object with `MAX_DOCUMENT_SIZE: int` (reuse the existing 50MB value from `src/analyzer.py`'s `MAX_FILE_SIZE`) and `SUPPORTED_FORMATS` (`.txt`, `.md`).
- No `OUTPUT_FORMAT` or other unused fields — only what `readers.py`/`analyzer.py` actually consume (avoids the YAGNI issue flagged in Phase A).
- Simple, explicit implementation — a small class or dataclass is fine; avoid over-engineering (no env-var loading unless requested).

### 2. `src/readers.py` (new)
- `read_document(file_path: str) -> str`
- Reuses the project's **existing exception hierarchy** from `src/exceptions.py` — `DocumentNotFoundError`, `UnsupportedFormatError`, `FileSizeExceededError`, `InvalidDocumentError` — not built-in exceptions (this corrects the Phase A mistake of raising `FileNotFoundError`).
- Validation order: path exists → is a file → format in `SUPPORTED_FORMATS` from `get_config()` → size ≤ `MAX_DOCUMENT_SIZE` from `get_config()` → read content.
- File reads use `with open(..., encoding="utf-8")` as a context manager. Use strict UTF-8 decoding (no `errors="replace"`) so bad encodings raise `InvalidDocumentError` with context rather than silently corrupting content — correcting the Phase A issue.
- Logs via `structlog.get_logger(__name__)` from `src.logging_config`, matching `analyzer.py`'s structured-logging style (event name + kwargs).
- Full type hints, imports ordered stdlib → third-party → local per CLAUDE.md.
- Empty file: returns `""` (no error) — consistent with current `extract_text` behavior on `empty_text_file`.

### 3. `src/analyzer.py` (modify, minimal)
- Replace hardcoded `MAX_FILE_SIZE` usage in `check_file_size()` with `get_config().MAX_DOCUMENT_SIZE`.
- No other refactoring — leave `validate_file_path`, `extract_text`, `analyze_text`, `process_document` signatures and behavior otherwise unchanged (per constraints.md: don't refactor beyond the feature's scope).

### 4. Tests
- `tests/test_config.py` (new): covers `get_config()` returns expected `MAX_DOCUMENT_SIZE` and `SUPPORTED_FORMATS`.
- `tests/test_readers.py` (new): covers `.txt` read, `.md` read, missing file → `DocumentNotFoundError`, unsupported extension → `UnsupportedFormatError`, oversized file → `FileSizeExceededError`, empty file → returns `""`, bad encoding → `InvalidDocumentError`.
- `tests/conftest.py`: add one fixture, `sample_markdown_file(tmp_path)`, following the exact pattern of `sample_text_file`.
- Reuse existing fixtures (`sample_text_file`, `empty_text_file`, `large_text_file`) rather than duplicating setup.

## Edge Cases Covered
- Empty file → returns `""`.
- File exceeds `MAX_DOCUMENT_SIZE` → `FileSizeExceededError`.
- Unreadable/invalid encoding → `InvalidDocumentError` (strict decode, not silently replaced).
- Non-existent path → `DocumentNotFoundError`.
- Unsupported extension (e.g. `.pdf`, `.csv`) → `UnsupportedFormatError`.
- Directory passed instead of file → `InvalidDocumentError` (mirrors `validate_file_path`'s existing `is_file()` check).

## Out of Scope (explicitly)
- PDF/DOCX support, batch/directory processing, CLI entry point, result caching.

## Verification
1. `uv run pytest` (or `python -m pytest`) — all existing 6 tests plus new tests pass.
2. `python -m pytest tests/test_readers.py tests/test_config.py -v` — confirm new tests pass individually.
3. Manually confirm `src/analyzer.py`'s `check_file_size` now sources its limit from `get_config()` instead of the module-level constant.
