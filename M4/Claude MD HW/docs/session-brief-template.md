# Session Brief

**Goal:** Extend document analyzer to support PDF and DOCX formats, currently only handles .txt files.

**Relevant files:**
- `src/analyzer.py` — extract_text() function needs multi-format support
- `tests/test_analyzer.py` — add extraction tests for PDF and DOCX
- `src/exceptions.py` — custom exception definitions
- `src/logging_config.py` — structlog setup (reference only)

**Constraints/boundaries:**
- Don't install new dependencies without approval (PDF/DOCX parsing libs not yet added)
- Don't refactor existing analyzer structure; only extend extract_text()
- File size limit: 50MB max (see config.MAX_DOCUMENT_SIZE)
- No print() for debugging—use structlog only
- Mock external API calls in tests; no real network calls

**Carryover decisions:**
- All imports must be at top of file, never inside functions (clarified in prior session)
- Use pytest fixtures for test data; don't inline file setup/cleanup
- Type hints required on all function signatures
- Use context managers for file operations; validate paths before opening
