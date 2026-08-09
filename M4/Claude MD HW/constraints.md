# Constraints

Negative constraints prevent agent overreach. Each constraint lists what NOT to do and provides an alternative action.

**Don't create new files or directories without explicit request.**
→ Instead, add code to existing files or ask which file to create and where.

**Don't install new dependencies without stating the reason and checking compatibility.**
→ Instead, explain why the dependency is needed, check its license and maintenance status, and wait for approval before running `pip install` or modifying `requirements.txt`.

**Don't use `print()` for debugging or logging.**
→ Instead, use `structlog.get_logger()` configured in `src/logging_config.py` as described in CLAUDE.md.

**Don't write tests that depend on external API calls or network access.**
→ Instead, mock external calls using `pytest-mock` or `unittest.mock.patch` with recorded responses or fixture data.

**Don't refactor existing code while implementing a feature.**
→ Instead, complete the feature first with minimal changes, then propose refactoring as a separate request with clear scope.

**Don't commit `.env` files or hardcoded secrets.**
→ Instead, add secrets to `.env.example` as templates and load them via environment variables at runtime using `python-dotenv`.
