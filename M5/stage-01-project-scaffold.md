cd # Stage 1 - Project Scaffold

**Lesson:** 1 of 5 (Python Environment and uv)
**Prerequisites:** Python 3.11+ installed (Stage 2 uses `asyncio.TaskGroup`, added in 3.11 - and `uv` will fetch a suitable interpreter if you don't have one), Git configured, GitHub account, editor, funded Anthropic API key available, `uv` installed

## Context

Every AI project starts here: a reproducible environment with a locked dependency set, isolated from the rest of your system. AI Python projects are especially fragile - `anthropic`, `httpx`, `pydantic`, `numpy`, and their transitive dependencies routinely conflict on patch versions. A clean scaffold prevents the "works on my machine" class of failures before they start.

The key word is **reproducible**. Declaring `anthropic>=0.40.0` says which versions are *acceptable*; it does not say which version your teammate will actually get. A lockfile does.

In this stage, you build the project foundation your capstone will stand on for the rest of the course.

> **Volatile layer.** `uv` moves quickly. Every command here was verified against **uv 0.11.28**. Run `uv --version` first; if yours differs, check the output shapes below against what you actually see and trust your terminal over this document.
>
> **If you are on uv 0.12 or newer**, three things below will look different, and none of them break the exercise:
>
> - `uv init` is packaged with a src layout **by default**. `--package` still works and still does what Step 1 describes; it is just no longer the flag that causes it. The opt-out is now `--no-package`.
> - The `[build-system]` block in Step 3 will say `uv_build>=0.12.x,<0.13` rather than `uv_build>=0.11.28,<0.12.0`. That is your uv version writing its own bound - leave it alone.
> - Pre-release handling defaults to `if-necessary`, so uv prefers a stable release over a pre-release unless a constraint forces one.

---

## Steps

### Step 1 - Create the Project

```bash
uv init --package capstone-ai --python 3.11
cd capstone-ai
```

`--python 3.11` flags to UV what Python version you want. Without it, `uv init` records whatever interpreter it happened to find on *your* machine into `requires-python` - so your `pyproject.toml` would claim a floor that is an accident of your laptop rather than a decision. State it, because the project has a real minimum: Stage 2 builds on `asyncio.TaskGroup`, which arrived in Python 3.11. If you don't have 3.11, uv downloads it; you do not need to install Python yourself.

`--package` gives you a **src layout** (`src/capstone_ai/`) rather than a flat one. As we said, src layout forces you to install your package before importing it, which catches a common class of bug: code that works in development because Python happened to find the local directory, and fails in production because the package was never installed properly.

Look at what `uv init` created:

```bash
ls -a
```

You should see `pyproject.toml`, `.python-version`, `README.md`, `src/` - and also `.git/` and `.gitignore`. Note that you did not run `git init`: `uv init` created the repository for you. The `.python-version` file pins the interpreter version for this project - `uv` reads it and will fetch that Python for you if it isn't installed.

Now read the `.gitignore` uv wrote, before you replace it:

```bash
cat .gitignore
```

It covers `__pycache__/`, `*.py[oc]`, `build/`, `dist/`, `wheels/`, `*.egg-info`, and `.venv`. **It does not cover `.env`.** Remember: a good default is not a secrets policy, and the thing that would leak your API key is exactly the line the tool did not write. Replace it with a list that does:

```bash
cat > .gitignore << 'EOF'
# Python-generated files
__pycache__/
*.py[oc]
dist/
*.egg-info/
.pytest_cache/
.mypy_cache/
wheels/
build/

# Virtual environments
.env
.venv/
EOF
```

Do this now, in Step 1, before Step 6 creates a file with a real key in it. Order is the point - a key committed once is in the history whether or not you delete the file afterwards.

Note what is **not** in that list either: `uv.lock`. The lockfile is committed deliberately - see Step 3.

If you see `fatal: not a git repository` on later steps, you're in the wrong directory. Run `pwd` and confirm you're inside `capstone-ai/`.

### Step 2 - Add Your Dependencies

Don't hand-write the dependency list. Let `uv` write it, then read what it wrote:

```bash
uv add "anthropic>=0.40.0,<1.0" "httpx>=0.27.0,<1.0" "pydantic>=2.5.0,<3.0" "pydantic-settings>=2.0,<3.0" "python-dotenv>=1.0.0,<2.0"
```

This is your first look at the speed difference: roughly twenty packages resolved, downloaded, and installed in a couple of seconds.

Three things just happened:

1. The constraints were written into `[project] dependencies` in `pyproject.toml`.
2. A `uv.lock` file was created, recording the **exact** version of every package, direct and transitive.
3. A `.venv/` was created and populated - **including your own project, installed in editable mode.** There is no separate "install my package" step and no `activate` step.

Now add the development tools, which belong in a *dependency group* rather than in your runtime dependencies:

```bash
uv add --dev "pytest>=8.0" "pytest-asyncio>=0.24.0" "ruff>=0.5.0"
```

And the server dependencies, which belong in an *extra*:

```bash
uv add --optional server "fastapi>=0.115.0,<1.0" "uvicorn[standard]>=0.30.0,<1.0"
```

**Groups vs. extras** An **extra** (`[project.optional-dependencies]`) is a consumer-facing optional feature: someone installing your package can ask for `capstone-ai[server]` and get the web server bits. A **dependency group** (`[dependency-groups]`) is developer-only: it is never published with your package and nobody installing your project downstream can pull it in. `pytest` is not a feature of your application, `fastapi` is.

### Step 3 - Read Your `pyproject.toml`

Open it. You did not write this by hand, so read it as carefully:

```toml
[project]
name = "capstone-ai"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
authors = [
    { name = "Your Name", email = "you@example.com" }
]
requires-python = ">=3.11"
dependencies = [
    "anthropic>=0.40.0,<1.0",
    "httpx>=0.27.0,<1.0",
    "pydantic>=2.5.0,<3.0",
    "pydantic-settings>=2.0,<3.0",
    "python-dotenv>=1.0.0,<2.0",
]

[project.scripts]
capstone-ai = "capstone_ai:main"

[project.optional-dependencies]
server = [
    "fastapi>=0.115.0,<1.0",
    "uvicorn[standard]>=0.30.0,<1.0",
]

[build-system]
requires = ["uv_build>=0.11.28,<0.12.0"]
build-backend = "uv_build"

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24.0",
    "ruff>=0.5.0",
]
```

Your `authors` line will show your own name and email - `uv init` reads them from your git config, so it differs from the block above and from your neighbour's.

Two of those lines are placeholders `uv init` left for you. Replace `description` with a sentence describing what your capstone actually does, and write that same sentence into the empty `README.md`. Keep `name = "capstone-ai"` as it is - every later lab stage and all of M4 import `capstone_ai` by that name. The project is yours; the package name is the course's.

Add the tool configuration by hand at the end - you'll need both from Stage 5 onward:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
target-version = "py311"
line-length = 100
```

Key decisions to understand:

- **Version pins use lower-bound + upper-bound** (`>=0.40.0,<1.0`), not exact pins. This states your *compatibility policy*: patch and minor updates are welcome, major versions are not, because they break APIs.
- **`[project.scripts]` is your console entry point.** `uv init --package` wired the command `capstone-ai` to the `main()` function in `src/capstone_ai/__init__.py`. That is why `uv run capstone-ai` works before you have written any code, and it is the section that would break if you renamed the package. You fill in that function in Step 5.
- **`pyproject.toml` is the policy; `uv.lock` is the fact.** The first says what you'd accept. The second says what you got. You need both, becuase they answer different questions.
- **`uv.lock` is committed.** This is why it is reproducible. Now open `uv.lock` and look at it - it records every transitive package with hashes. You will never edit this file by hand.

### Step 4 - Sync and Prove Reproducibility

Try:
```bash
uv sync 
```


```bash
uv sync --extra server
```

`uv sync` makes your environment match the lockfile exactly - installing what's missing and **removing what shouldn't be there**. Note the `--extra server`: by default `uv sync` installs your dependencies and your default groups, but *not* extras. If you skip the flag, watch `uv` uninstall `fastapi` and friends, and you'll have learned the rule the memorable way.

Now, the version of this command you will use in production:

```bash
uv sync --locked --extra server
```

Expected: it succeeds. `--locked` means *"install from the lockfile and fail if the lockfile is out of date"* - which is exactly what you want in CI, where a silently-updated dependency is how a build starts differing from a developer's machine.

Note that `--extra server` is needed here as well. The two flags answer different questions: `--locked` asserts the lockfile is current, `--extra` selects which optional dependencies you want installed. **Every sync re-states its extras** - leave the flag off and `uv` will do exactly what you just watched it do and remove `fastapi` again.

Prove it actually catches drift. Add a dependency to `pyproject.toml` by hand (say `"rich>=13.0"` in `dependencies`) and run it again:

```bash
uv sync --locked --extra server
```

Expected:

```
error: The lockfile at `uv.lock` needs to be updated, but `--locked` was provided.

hint: To update the lockfile, run `uv lock`.
```

Remove the line you added. **This is the answer to "will my teammate get the same environment?"** - a gate that fails loudly.
However, it is important to understand that when you get that message, you should NOT run uv lock, fix it and carry on. You need to understand what changed,
why, and decide whether to keep the change and change the lockfile OR discard the change, and that decision needs to be propogated through the team.

`uv lock --check` performs the same verification without touching the environment; it's the cheaper form for a CI lint job.

### Step 5 - Set Up the Project Directory Structure

`uv init --package` gave you `src/capstone_ai/` - and inside it, an `__init__.py` holding a placeholder entry point:

```python
def main() -> None:
    print("Hello from capstone-ai!")
```

`[project.scripts]` in your `pyproject.toml` routes the console command `capstone-ai` to this function, which is why `uv run capstone-ai` already works. Replace the `print` with something your capstone would actually do on startup, then confirm the wiring still holds:

```bash
uv run capstone-ai
```

$ uv run capstone-ai
      Built capstone-ai @ file:///C:/Users/Owner/Documents/capstone-ai         ⠙Uninstalled 1 package in 1ms
Installed 1 package in 74ms
Hello! Please upload the Fathom files from the meeting or the user requirements document.



Now fill in the structure the rest of the course expects:

```bash
mkdir -p src/capstone_ai/{api,core,prompts}
mkdir -p tests/{unit,integration,eval}
```

Create the package init files:

```bash
touch src/capstone_ai/api/__init__.py
touch src/capstone_ai/core/__init__.py
touch src/capstone_ai/prompts/__init__.py
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py
touch tests/eval/__init__.py
```

Create the config module:

```python
# src/capstone_ai/core/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    model_name: str = "claude-sonnet-5"
    max_tokens: int = 4096

    model_config = {"env_file": ".env", "env_prefix": ""}


settings = Settings()
```

You don't need to reinstall anything after adding source files - the editable install picks them up.

Now write the smoke tests. They are deliberately small; what each one can actually catch is spelled out below:

```python
# tests/unit/test_setup.py
"""Scaffold smoke tests - these fail loudly if the environment is wrong."""


def test_environment_matches_the_lockfile():
    import anthropic
    import httpx
    import pydantic

    assert pydantic.VERSION.startswith("2."), "pydantic-settings needs Pydantic v2"


def test_own_package_is_installed():
    """src layout means capstone_ai must be *installed*, not merely present on disk."""
    from capstone_ai.core.config import Settings

    assert Settings().max_tokens > 0


def test_python_is_new_enough_for_stage_2():
    """Lab Stage 2 uses asyncio.TaskGroup, added in Python 3.11."""
    import asyncio
    import sys

    assert sys.version_info >= (3, 11), f"Stage 2 needs Python 3.11+, this is {sys.version.split()[0]}"
    assert hasattr(asyncio, "TaskGroup")
```

The first is a sentinel rather than coverage. In an environment built by `uv sync --locked` those packages are present by construction, so each import and the version assert can fail for exactly one reason: you are running against an environment the lockfile did not build - a stale `.venv`, the system Python, something `pip install`ed by hand. That is one check written four times, which is worth one cheap test and no more. Note what it is *not*: it is not what catches the Pydantic conflict in Step 10. That conflict is caught by `uv lock` refusing to resolve, one step earlier - the environment is never rebuilt, so the tests never see Pydantic v1.

The second is the only check in this stage that proves what Step 1 claimed about src layout: it imports your package from `tests/`, which is where a broken editable install shows up.

The third exists because of a failure this stage cannot otherwise catch. Every dependency here installs happily on Python 3.10 - so without this test you would finish Stage 1 with everything green, and discover in Stage 2 that `asyncio.TaskGroup` does not exist on your interpreter. The `--python 3.11` in Step 1 should make it impossible; the test is what tells you if it didn't. Note that it asserts the version *and* checks the attribute: the version gives you an actionable message, the `hasattr` proves the capability rather than trusting a number.

Note that none of the three reads `.env`; `Settings()` has a default for every field. Tests that need .env don't run in CI.

### Step 6 - Configure Secrets Management

Verify `.env` is in `.gitignore`:

```bash
grep "\.env" .gitignore
```

If you don't see `.env` in the output, add it immediately - never commit API keys.

Create `.env` in the project root:

```bash
cat > .env << 'EOF'
ANTHROPIC_API_KEY=sk-ant-your-key-here
EOF
```

Replace `sk-ant-your-key-here` with your actual API key.

Create a `.env.example` that IS committed (without the real key):

```bash
cat > .env.example << 'EOF'
ANTHROPIC_API_KEY=sk-ant-your-key-here
EOF
```

Verify the config loads:

```bash
uv run python -c "from capstone_ai.core.config import settings; print(f'Key loaded: {bool(settings.anthropic_api_key)}')"
```

Expected: `Key loaded: True`. If you see `Key loaded: False`, check that your `.env` file is in the project root (same directory as `pyproject.toml`).

Note `uv run`: it executes inside the project environment without you activating anything. If you prefer an activated shell you can still `source .venv/bin/activate`, but every command in this course works without it.

### Step 7 - Run a Dependency Audit

```bash
uv audit
```

Expected on a fresh scaffold: `Found no known vulnerabilities and no adverse project statuses in N packages`, where `N` is in the mid-thirties. The exact count moves whenever a dependency changes its own requirements, so check the *shape* of the line, not the number.

You will also see a warning that `uv audit` is experimental. It is, as of 0.11.28 - pass `--preview-features audit-command` to silence the warning, and be aware the interface may change. If you want a stable tool with the same job, `uvx pip-audit` runs the established `pip-audit` in a throwaway environment without adding it to your project:

```bash
uvx pip-audit
```

Either way, review the output. If vulnerabilities are found:

1. Note the package and the CVE.
2. Find who pulled it in: `uv tree --invert --package <name>` shows the path *up* from that dependency to your project. The `--invert` matters - without it you get the package's own dependencies, which is the opposite question. Transitive vulnerabilities usually get fixed by bumping the direct dependency that requires them.
3. Adjust the constraint in `pyproject.toml`, run `uv lock`, and re-audit.
4. If the fix requires a breaking change, note it for later review.

Also check what's fallen behind:

```bash
uv tree --outdated --depth 1
```

You don't need to update everything - just be aware of what's behind.

**There is no `pip check` step here, and its absence is the lesson.** `pip check` exists because pip installs packages one at a time and can leave you with a broken set. `uv sync` resolves the whole graph and then makes the environment match it, so an inconsistent environment isn't a state you can reach. You verified this already in Step 4 - `uv sync --locked` is the check.

### Step 8 - Verify the Full Setup

Run these verification checks in sequence:

```bash
# Verify the interpreter uv is using
uv run python --version

# Verify key packages import
uv run python -c "import anthropic; print(f'anthropic {anthropic.__version__}')"
uv run python -c "import httpx; print(f'httpx {httpx.__version__}')"
uv run python -c "import pydantic; print(f'pydantic {pydantic.VERSION}')"
uv run python -c "import fastapi; print(f'fastapi {fastapi.__version__}')"

# Verify config loads with API key
uv run python -c "from capstone_ai.core.config import settings; print(f'Config OK, key present: {bool(settings.anthropic_api_key)}')"

# Verify the environment matches the lockfile (with the extra, so fastapi stays installed)
uv sync --locked --extra server

# Verify the test suite runs - and that your own package is importable
uv run pytest -q
```

All checks should pass without errors. The last one should report `3 passed` - if it reports `no tests ran`, your test file isn't where pytest is looking; check `testpaths` in `pyproject.toml` and the filename (`test_*.py`).

### Step 9 - Initial Commit

```bash
git add .
git status
```

Review what's staged. Two things to confirm:

- `.env` is **NOT** listed (it should be gitignored). If it appears, abort and fix `.gitignore` before committing.
- `uv.lock` **IS** listed. If it's missing, you gitignored it by mistake - remove it from `.gitignore`. Committing the lockfile is the whole point.

```bash
git commit -m "M3-stage-01: uv project scaffold with locked dependencies, src layout, config"
```

### Step 10 - Deliberate Dependency Conflict

This step is intentionally adversarial. You'll introduce a dependency conflict and resolve it.

Your project depends on `pydantic-settings` - that's what `core/config.py` uses to load `.env`. `pydantic-settings` v2 requires Pydantic v2. Now pretend a teammate insists on Pydantic v1 for some legacy code. Edit `pyproject.toml`:

```toml
dependencies = [
    "anthropic>=0.40.0,<1.0",
    "httpx>=0.27.0,<1.0",
    "pydantic>=1.0,<2.0",          # intentional conflict
    "pydantic-settings>=2.0,<3.0",
    "python-dotenv>=1.0.0,<2.0",
]
```

Now try to lock:

```bash
uv lock
```

Expected - roughly 47 lines, most of which is a list of every `pydantic-settings` version available. Don't let the volume scare you; read the top line and the bottom paragraph:

```
  × No solution found when resolving dependencies:
  ╰─▶ Because only the following versions of pydantic-settings are available:
          pydantic-settings<=2.0.0
          pydantic-settings==2.0.1
          ... (about thirty-five lines of versions) ...
      and pydantic-settings==2.0.0 depends on pydantic>=2.0b3, we can conclude
      that pydantic-settings>=2.0.0,<2.0.1 depends on pydantic>=2.0b3.
      ...
      And because pydantic-settings>=2.3.0 depends on pydantic>=2.7.0 and your
      project depends on pydantic>=1.0,<2.0, we can conclude that your project
      and pydantic-settings>=2.0.0 are incompatible.
      And because your project depends on pydantic-settings>=2.0 and your
      project requires capstone-ai[server], we can conclude that your
      project's requirements are unsatisfiable.
```

Read what that actually is: a **proof**. Each "And because... we can conclude..." is one step of reasoning from your constraints to the contradiction. The resolver isn't reporting a failure, it's showing its work. The last two sentences name the two facts that can't both be true: you asked for `pydantic<2.0`, and you asked for `pydantic-settings>=2.0`, which needs `pydantic>=2.7.0`.

The middle section - every available version enumerated - is there so you can see the search space was genuinely exhausted, not sampled. Skip it on first read and come back to it if the conclusion surprises you.

Fix the constraint back to `>=2.5.0,<3.0`, run `uv lock`, and confirm it resolves.

Record in a comment or note: what happened, what the error said, and how you resolved it. Specifically: **which line of the proof would you have to change to make this solvable?**

Error: I changed pydantic requirement to >=1.0,<2.0 (Pydantic v1), but pydantic-settings>=2.0 requires pydantic>=2.0 (Pydantic v2). They're incompatible.

Which line to change: The line in the dependency proof that reads:

your project depends on pydantic>=1.0,<2.0

> **Worth knowing:** you might expect `anthropic` to be the package that forces Pydantic v2 - it's the obvious suspect in an AI project. It isn't. As of `anthropic` 0.121.0 the declared constraint is `pydantic<3,>=1.9.0`, so the SDK itself is happy with v1. (The version number moves every few weeks; that constraint has been stable.) Check for yourself: `uv run python -c "import importlib.metadata as m; print([r for r in m.requires('anthropic') if 'pydantic' in r])"`. The lesson generalizes: the package that *breaks* your resolve is rarely the one you'd guess, which is why you read the proof instead of assuming.

---

## Success Criteria

You're done when:

- [x] `pyproject.toml` exists with dependencies in three places: runtime (`dependencies`), a `server` extra, and a `dev` group
- [x] `uv.lock` exists and is committed to git
- [x] `uv sync --locked` succeeds
- [x] `.env` contains your API key and is NOT tracked by git
- [x] `uv run python -c "from capstone_ai.core.config import settings; print(settings.anthropic_api_key[:10])"` prints the first 10 characters of your key
- [x] `uv audit` runs without critical vulnerabilities
- [x] The project directory has `src/capstone_ai/{api,core,prompts}` and `tests/{unit,integration,eval}`
- [x] `uv run pytest` passes (3 tests)
- [x] An initial commit exists with the scaffold (with `uv.lock` in it and `.env` not)

## Quality Checklist (Best Practices Ownership)

Evaluate your scaffold against these criteria. For any "no," fix it and explain why it matters.

- [x] **Version policy:** Every *runtime and extra* dependency has both a lower bound and an upper bound (not just `>=`), and you can say what the upper bound is protecting you from. Your `dev` group is deliberately exempt, and you can say why: a dev tool that breaks fails loudly in your own CI, where you fix it; a runtime dependency that breaks fails silently in a consumer's install, where you never see it. Bounds protect people who aren't in the room. Capping `ruff` - pre-1.0, shipping fixes in minor releases - would cost you those fixes to protect nobody
- [x] **Groups vs. extras:** Dev tooling is in `[dependency-groups]`, optional runtime features are in `[project.optional-dependencies]` - and you can explain why `pytest` is not an extra
- [x] **Secrets isolation:** `.env` is gitignored, `.env.example` is committed, no API key appears in any tracked file
- [x] **Reproducibility:** You can state what `uv.lock` gives you that `pyproject.toml` cannot, and name the command that enforces it in CI - a teammate cloning this repo gets byte-identical versions, not merely compatible ones
- [x] **Audit reviewed:** You read the `uv audit` output rather than just watching it exit 0, and you know how to trace a transitive finding back to the direct dependency that pulled it in (`uv tree --invert --package <name>`)
- [x] **Tests that assert:** pytest is configured in `pyproject.toml` (`asyncio_mode`, `testpaths`) *and* `tests/unit/test_setup.py` makes assertions that could actually fail - a test that only imports is a test that passes when the thing it checks is broken
- [x] **src layout:** Your package lives under `src/` and imports work because it is *installed*, not because Python happened to find the directory - and you can say why that catches a class of bug the flat layout hides
- [x] **Clean history:** Your first commit contains `uv.lock` and contains no `.env`, `.venv/`, or `__pycache__/` - check what is *in* the commit, not just that one exists

## Explain It Back

After your scaffold is working, answer in writing (3-5 sentences):

1. `pyproject.toml` says `anthropic>=0.40.0,<1.0` and `uv.lock` says one exact version. Why do you need both files? What question does each one answer?
2. What went wrong in the deliberate conflict step? Name the two constraints that couldn't both hold, and say how you found them in the output.
3. Your CI pipeline could run `uv sync` or `uv sync --locked`. Which one should you use, and what breaks if you pick the other?
4. If you needed to add `torch` to this project, what new dependency conflicts would you anticipate?

ANSWERS:

1. pyproject.toml defines acceptable version ranges; uv.lock pins exact versions. You need both: ranges let you upgrade intentionally, lock ensures reproducibility across machines.

2. Because pydantic-settings>=2.0.0 depends on pydantic>=2.0b3 
And because the intentional conflict depends on pydantic>=1.0,<2.0
We conclude that the intentional conflict and pydantic-settings>=2.0.0 are incompatible.

3. Use uv sync --locked. Without --locked, CI re-resolves and could deploy untested versions.

4. Torch pins strict CUDA/numpy versions; likely conflicts with existing dependency ranges. You'd need to pin torch carefully and regenerate the lock.

## Stretch Goals

- **Export for a pip-only consumer:** Run `uv export --format requirements-txt > requirements.txt`. Some platforms and CI systems still expect that file. Note that it's a *generated artifact* now, not a source of truth - and consider whether you'd commit it.
- **Add a Makefile:** Create a `Makefile` with targets for `sync`, `test`, `audit`, and `lint`. This pays off starting Stage 5.
- **Try `uv python`:** Run `uv python list` and `uv python pin 3.12`. uv manages interpreters too - see what changes in `.python-version` and what `uv sync` does next.

## Common Pitfalls

| Problem | What You See | Recovery |
|---|---|---|
| Wrong Python version | `requires-python` error on sync | Run `uv python list`. uv can install a suitable version for you: `uv python install 3.11`. |
| Extras silently removed | `fastapi` vanishes after `uv sync` | You omitted `--extra server`. `uv sync` makes the env match the lockfile's *default* set; extras are opt-in. |
| `.env` committed to git | `git status` shows `.env` as tracked | `git rm --cached .env`, add `.env` to `.gitignore`, commit the fix. |
| `uv.lock` NOT committed | Teammate gets different versions | Check `.gitignore` - remove any `uv.lock` entry. The lockfile belongs in git. |
| `ModuleNotFoundError` on import | Package installed but can't be found | Run `uv sync`. Your own package is installed editable by sync - there is no separate install step to forget. |
| Lockfile "needs to be updated" in CI | `uv sync --locked` fails on the build machine | Someone edited `pyproject.toml` without running `uv lock`. Run `uv lock` locally and commit the result. |

## Connection to Next Stage

Your project scaffold is now reproducible and secure - and "reproducible" now means a lockfile, not a hope. In Stage 2, you'll build the async HTTP client layer on top of this foundation: the concurrency pattern that makes AI API calls fast. The `httpx` and `asyncio` libraries you installed here are the building blocks.
