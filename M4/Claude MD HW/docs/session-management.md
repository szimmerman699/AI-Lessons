# Session Management: Document Analyzer

A practical guide for starting a productive session six months from now.

## Quick Setup (5 min)

```bash
# Check Python version (should be 3.11+)
python --version

# Activate venv from repo root
source .venv/Scripts/activate  # or .venv\Scripts\activate on Windows

# Install/update dependencies
pip install -r requirements.txt

# Verify test suite runs
pytest tests/ -q

# Copy env template if .env doesn't exist
cp .env.example .env
# Edit .env with actual credentials (API keys, paths, etc.)
```

If pytest fails:
- Check Python version (3.11+)
- Delete `.venv` and reinstall: `python -m venv .venv && pip install -r requirements.txt`
- Clear pytest cache: `rm -rf .pytest_cache` (or PowerShell equivalent)

## Key Files at a Glance

| File | Purpose | Key Point |
|------|---------|-----------|
| `src/analyzer.py` | Core logic: extract_text(), process_document(), analyze_content() | Main module; all public functions need type hints |
| `src/exceptions.py` | Custom exceptions (InvalidFileType, DocumentSizeError, etc.) | Use these, never bare Exception |
| `src/logging_config.py` | structlog setup | Always use `structlog.get_logger()`, never print() |
| `src/config.py` | Constants (MAX_DOCUMENT_SIZE=50MB, timeouts, etc.) | Reference, don't hardcode values |
| `tests/conftest.py` | pytest fixtures (sample files, mock objects) | Add new fixtures here, not in individual test files |
| `tests/test_analyzer.py` | 24 tests across 6 test classes | Edit here for new tests |
| `.env.example` | Environment variable template | Copy to .env, never commit .env |
| `CLAUDE.md` | Rules for Claude sessions | Read the "Coding Conventions" section |
| `constraints.md` | What NOT to do | Review if you hit a blocker or need to refactor |

## Session Workflows

### Adding a Feature

1. **Read CLAUDE.md** — Refresh on type hints, import ordering, logging style
2. **Write the function** in `src/analyzer.py` with full type hints
3. **Write tests first** (or alongside):
   - Add fixture to `tests/conftest.py` if needed
   - Add test class/methods to `tests/test_analyzer.py`
   - Aim for edge cases, not just happy path
4. **Check coverage:** `pytest tests/ --cov=src --cov-report=html` (need ≥85%)
5. **Run all tests:** `pytest tests/ -v`
6. **Commit:** Include clear message explaining the feature

### Debugging a Failing Test

```bash
# Run single test with output
pytest tests/test_analyzer.py::TestExtractText::test_extract_text_valid_file -vv

# Run with pdb on failure
pytest tests/test_analyzer.py::TestExtractText::test_extract_text_valid_file --pdb

# Show print/log output (tests suppress by default)
pytest tests/test_analyzer.py::TestExtractText -s
```

**Common issues:**
- **Import errors:** Check import ordering (stdlib → third-party → local, all at top of file)
- **FileNotFoundError:** Use fixtures (tmp_path, sample_files) not hardcoded paths
- **AssertionError:** Use `pytest -vv` to see expected vs. actual; add descriptive assertion messages
- **Coverage gaps:** Check which lines aren't covered: `coverage report -m`

### Refactoring

**STOP:** Read `constraints.md` first. Refactoring without explicit request is blocked.

If you have a refactoring idea:
1. Propose it with clear scope (e.g., "extract PDF parsing to separate module")
2. Don't mix with feature work; refactoring is a separate request
3. Ensure tests still pass and coverage ≥85%

### Code Review / Bug Hunt

Use Sonnet 5 or Opus 5 for review (see `docs/model-routing.md`). Key checks:
- Type hints on all functions (no `Any` without reason)
- Logging with structlog, no print()
- Specific exceptions (ValueError, FileNotFoundError), not bare Exception
- Context managers for file I/O
- Test coverage ≥85%

## Context Rot: Symptoms & Recovery

Context rot is attention dilution masquerading as capability loss. The window still has space, but signal is drowning in noise. You recognize it before it cripples the session.

### Symptom Card: The Four Signs

When any of these appear, suspect context rot **before** blaming the model:

1. **Claude ignores a CLAUDE.md rule it was following earlier in the same session.**
   - Example: Started with type hints on all functions, five requests later skips them. No new rule was added; attention just shifted.

2. **Output goes generic.** 
   - It could be for any project. Has lost your naming conventions, project structure, your specific patterns. Sounds like a default tutorial instead of your codebase.

3. **Claude references a decision, file, or conversation that never happened.**
   - "I see you already refactored extract_text()" — but you didn't. "Let's update the API key in config.py" — there is no config.py.

4. **Claude re-asks for information you already gave it.**
   - "What are the test constraints?" — you answered this three requests ago. The token is there; attention is just elsewhere.

### Your First Diagnostic Move

**Run `/context` and look at three numbers:**

- **Total window used:** 60k/200k (30%)? You're fine. 140k/200k (70%)? Getting close. 180k/200k (90%)? This is the clock.
- **But more important — the percentage breakdown.** If you're at 25% total but messages are 15% and growing, you have a dilution problem *before* the window is full.
- **Which component grew most?** Check: System prompt (fixed), Tools (fixed), Messages (this is you and tool output). If messages are > 50% of total, explore why. One large file read or verbose command output can dwarf everything you typed.

**The critical distinction:** Rot is attention dilution, not a full window. If `/context` shows you at 12% of the window and quality has dropped, "I ran out of space" is not the explanation. Do not wait for a full window to act. Act at 30-40% if the composition looks wrong.

### Your Personal Tell

_[Leave this empty until a real session degrades. When it does, fill in: What was the very first signal you noticed before you had numbers to back it up? A subtle wrong fact? A name that didn't belong? A tone that felt off?]_

### When to Reach for Each Recovery

- **Fresh session / `/clear`** — When you've switched topics radically or accumulated tool output from work you're done with. A brief restarts the conversation while CLAUDE.md reloads automatically.
- **Proactive `/compact`** — Before quality starts sliding. Explicit Keep/Summarize/Discard instructions prevent old decisions from being summarized away.
- **`/rewind`** — When you went down a path that broke things or loaded a lot of noise. Restores both files *and* conversation, unlike git checkout.
- **Subagent delegation** — For high-volume, low-density work (research, library comparison, documentation surveys). Returns only the conclusion; keeps exploration out of your main context.

## Rules to Remember

These are the top 5 rules from CLAUDE.md. **Don't memorize—bookmark CLAUDE.md and skim when in doubt.**

1. **Type hints required.** Every function signature: `def extract_text(file_path: str) -> str:`
2. **Imports at top.** All imports at file start, stdlib → third-party → local. NO inline imports in functions.
3. **Use structlog.** `logger = structlog.get_logger()` then `logger.info("event", key=value)`. Never `print()`.
4. **Specific exceptions.** Raise `FileNotFoundError`, `ValueError`, `NotImplementedError`. Don't catch bare `Exception`.
5. **File context managers.** Always `with open(...) as f:` Never bare open/close.

**Bonus:** Never commit `.env` files. Secrets go in `.env.example` as templates.

## Test Suite Quick Reference

```bash
# Run all tests
pytest tests/

# Run tests in one file
pytest tests/test_analyzer.py

# Run one test class
pytest tests/test_analyzer.py::TestExtractText

# Run one test
pytest tests/test_analyzer.py::TestExtractText::test_extract_text_valid_file

# Verbose output (show test names, durations)
pytest tests/ -v

# Very verbose (show assertions)
pytest tests/ -vv

# With coverage report
pytest tests/ --cov=src --cov-report=html

# Stop on first failure
pytest tests/ -x

# Run only failed tests from last run
pytest tests/ --lf

# Show print/log output (normally suppressed)
pytest tests/ -s
```

**Always run** `pytest tests/ --cov=src` before committing. Coverage must be ≥85%.

## Environment Variables

**Never commit `.env`**. Use `.env.example` as template.

```bash
# Copy template
cp .env.example .env

# Edit with actual values
# Common vars:
# - API_KEY: external service (AI analysis, etc.)
# - LOG_LEVEL: DEBUG, INFO, WARNING, ERROR
# - MAX_WORKERS: thread pool size for batch processing
```

Secrets are loaded via `python-dotenv` in `src/config.py`. Code accesses them as `os.getenv("VAR_NAME")`.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Import errors on startup | Activate venv: `source .venv/Scripts/activate` |
| `ModuleNotFoundError: No module named 'src'` | Run from repo root, not inside `src/` directory |
| Tests fail but code works locally | Delete `.pytest_cache` and `__pycache__`, reinstall: `pip install -r requirements.txt` |
| Coverage report is wrong | Delete `.coverage` file, rerun pytest |
| `structlog` not logging anything | Check `LOG_LEVEL` in `.env` (default: INFO) and log level in code (`logger.debug(...)` won't show unless DEBUG) |
| Can't find fixture in tests | Check `tests/conftest.py`; fixtures are defined there, not in individual test files |
| Type hint errors (MyPy/Pyright) | Check import: `from typing import Optional, List, Dict` for complex types |

## Session Hygiene Defaults: Your Actual Habits

Build these into your muscle memory. They're not aspirational—they're the checks you'll actually do:

| Trigger | Action | Why |
|---------|--------|-----|
| **Start of session** | Run `/context` — record the baseline number | Proves you're not already drowning; gives you a reference point |
| **After 4-5 substantial requests** | Quick `/context` check — is composition still healthy? (Messages shouldn't jump >50%) | Catches dilution early while you still have headroom |
| **Output quality noticeably drops** | Before blaming yourself: run `/context`. If you're at 30-40% and quality fell, it's attention rot, not capability | Separates "I need a better answer" from "I need a clean context" |
| **Before committing code** | Ensure git is clean. This is your checkpoint before risky requests or `/rewind` | `/rewind` works best when git already has a known-good state |
| **End of session** | Run `/cost` once. Note the number. Is it what you expected? | Calibrates your intuition about what work costs |
| **Switching major topics mid-session** | Consider `/compact` instead of adding to the pile. "Keep old work, reset for new" | Prevents one feature's debug output from poisoning the next feature's focus |
| **Returning after >2 hours away** | Start a fresh session with brief. Don't reuse the old one. | Context has gone stale; mental model has reset anyway |

**The 3-minute check you'll actually do:** `/context` at the 4-request mark. That's it. If that number looks wrong, you know to act. Everything else flows from there.

---

## Carryover Decisions

From prior sessions (see CLAUDE.md for full context):

- **Import ordering:** Top of file, never inside functions. Stdlib → third-party → local, blank lines between groups.
- **Fixtures:** All test setup in `conftest.py`. Use `tmp_path` for temp files (don't create/delete manually).
- **Mocking:** Mock external APIs with `pytest-mock` or `unittest.mock.patch`. No real network calls in tests.
- **File encoding:** Always UTF-8 with error handling. Don't assume OS default encoding.

## Common Next Steps

After getting a session running:

1. **Check CLAUDE.md** for any new rules added since last session (see "Rule-Update Log")
2. **Run full test suite** to ensure nothing broke: `pytest tests/ --cov=src`
3. **Skim model-routing.md** if you're about to request a major feature (Opus vs. Sonnet choice)
4. **Reference session-brief-template.md** if starting a new feature request to Claude

## Commit Message Template

```
[Feature/Fix/Test/Docs] Brief one-line summary

- Detail 1: What changed and why
- Detail 2: Any edge cases handled
- Tests: Coverage maintained at ≥85%

Related to: [GitHub issue, if any]
```

Example:
```
[Feature] Add DOCX extraction to extract_text()

- Implemented extract_docx() using python-docx
- Integrated with extract_text() dispatcher
- Added 4 new tests; coverage 87% → 89%
- All existing tests pass

Related to: PDF/DOCX support epic
```

---

**Last updated:** August 2026  
**Python version:** 3.11+  
**Key dependency versions:** See requirements.txt
