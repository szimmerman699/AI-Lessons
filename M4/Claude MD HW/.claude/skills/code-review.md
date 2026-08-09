---
name: code-review
description: Review code changes against project conventions, security patterns, and test coverage
---

# Code Review Skill

## Trigger Conditions

Invoke this Skill when you need to:
- Review changes to `src/` files for adherence to CLAUDE.md rules
- Evaluate new tests for pytest conventions and fixture usage
- Audit code for security issues (hardcoded secrets, unvalidated input)
- Verify test coverage and error path testing
- Check logging, exception handling, and type hints

Run with: `/code-review` or when asked "review this code" or "check this for issues"

---

## Step-by-Step Review Process

### 1. Identify Changed Files

Read and list all files that were modified or created. Categorize:
- **Source code:** `src/*.py`
- **Tests:** `tests/*.py`
- **Config:** `requirements.txt`, `.env.example`, setup files

### 2. Check CLAUDE.md Conventions (src/ files only)

For each source file, verify:

- [ ] **Type hints:** Every function has full type hints including return type. Flag: `def analyze(text): ...` (missing return type)
- [ ] **Naming:** Functions are `snake_case`, classes are `PascalCase`, privates have `_leading_underscore`. Flag: `def Analyze(...)` or `MyVar = ...`
- [ ] **Import ordering:** stdlib → third-party → local, blank lines between groups, alphabetized. Flag: imports inside functions or classes
- [ ] **Logging:** Uses `structlog.get_logger()` from `src/logging_config.py`. Flag: `print()`, `logging.getLogger()`
- [ ] **Exceptions:** Raises specific exceptions (ValueError, FileNotFoundError, custom from src/exceptions.py). Flag: bare `Exception`, `pass` in except blocks
- [ ] **File handling:** Uses `with` context managers, validates paths, handles UTF-8 errors. Flag: `open()` without `with`, uncaught IOError

### 3. Test Coverage (tests/ files only)

For each test file, verify:

- [ ] **Framework:** pytest only. Flag: `unittest.TestCase`, `setUp/tearDown`, `unittest.mock`
- [ ] **Fixtures:** Uses fixtures as parameters (from conftest.py). Flag: setup code inside test functions, manual file cleanup
- [ ] **tmp_path:** Tests needing temp files use `tmp_path` fixture. Flag: `open('test.txt')` or `os.makedirs()`
- [ ] **Exception testing:** Uses `pytest.raises(SpecificError)`. Flag: try/except blocks, bare `Exception`
- [ ] **Error paths:** Tests both happy path and error cases. Flag: only successful scenarios, no exception testing
- [ ] **Coverage:** Aim for ≥85% on public functions. Check: are edge cases tested?

### 4. Security Audit

Check for:

- [ ] **Hardcoded secrets:** No API keys, tokens, passwords in code. Flag: `API_KEY = "sk-..."`, passwords in strings
- [ ] **Environment variables:** Secrets loaded from `.env` via `python-dotenv`. Check: `.env` is in `.gitignore`
- [ ] **Input validation:** File uploads checked for size, MIME type, malicious content. Flag: no validation, unsafe file operations
- [ ] **SQL/command injection:** No string interpolation in queries or system calls. Flag: `os.system(f"command {user_input}")`
- [ ] **Unvalidated user input:** All external input validated before use. Flag: direct use of request data

### 5. Error Handling Quality

Check:

- [ ] **Specific errors:** Custom exceptions defined and raised with context. Flag: generic `Exception`, missing error info
- [ ] **Logging on error:** Errors logged with `structlog` before re-raising (include context, not sensitive data)
- [ ] **Error messages:** User-facing messages are clear and actionable. Flag: "Error occurred", missing details
- [ ] **Retry/timeout logic:** External API calls have timeout, retry logic, backoff. Check `src/analyzer.py` patterns

### 6. Report Findings

Format findings as:

```
[PASS] ✓ All CLAUDE.md conventions followed
[PASS] ✓ pytest conventions, ≥85% coverage
[FAIL] src/analyzer.py:45 — Missing return type hint on `extract_text()`
[WARN] tests/test_analyzer.py:120 — `pytest.raises()` should specify exception type, not bare `Exception`
[FAIL] src/config.py:10 — Hardcoded API_KEY detected, should use os.environ
```

Include file:line references for each finding.

---

## What NOT to Do

- Don't fix the code—only report findings. The developer fixes it.
- Don't reformat code for style unless it violates CLAUDE.md (e.g., import ordering).
- Don't suggest refactoring unrelated to the current change (see constraints.md).
- Don't assume changes are correct—audit security, types, and tests rigorously.

---

## Example Invocation

**Request:** "Review the changes I made to src/analyzer.py"

**Skill response:**
1. Read the modified file
2. Check against each CLAUDE.md rule
3. Verify tests exist and use fixtures correctly
4. Audit for security issues
5. Report: `[PASS] All conventions followed` or `[FAIL] X violations found` with line numbers

---

## Success Criteria

A Skill review is complete when:
- ✓ All CLAUDE.md rules have been checked
- ✓ Test coverage and pytest conventions verified
- ✓ Security audit performed
- ✓ Findings reported with file:line references
- ✓ Severity level assigned ([PASS], [WARN], [FAIL])
