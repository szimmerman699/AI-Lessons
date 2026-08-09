# Homework - CLAUDE.md For Python Projects

**Module:** M2 - Context Engineering & Claude Code
**Lesson:** 2 of 4
**Audience:** AI Engineer (developer track)
**Format:** Homework — worked top to bottom. Due before the next meeting.
**Prereqs:** Claude Code installed with a working API key. The provided starter project (Document Analyzer).

> **This is homework.** The meeting was lecture and a live demo; here you build the persistent-context layer yourself. Work top to bottom — later parts build on earlier ones.

## Context

Every Claude Code session starts fresh - Claude knows nothing about your project until you tell it. In Lesson 1, you saw this firsthand: Claude guessed the testing framework, import conventions, and project structure. Sometimes it guessed right. Often it didn't.

CLAUDE.md fixes this. It's a markdown file at your project root that Claude reads automatically at the start of every session. Write it once, and Claude starts every session with accurate context about your project.

You'll do this on the provided **starter project** (a small "Document Analyzer"). It deliberately ships a *weak* CLAUDE.md (vague rules like "write clean code") and a test file that uses `unittest` instead of pytest - both are there for you to fix. You'll rewrite the CLAUDE.md, apply the rule-update pattern to refine it, create a `constraints.md` to prevent agent overreach, and build a reusable Skill. You'll bring this same layer to your own capstone in later modules, once it has code.

---

## Success Criteria

You're done when:

1. The starter project has a rewritten CLAUDE.md with at least 10 specific, actionable rules covering: project structure, stack, coding conventions, testing, and production constraints.
2. You have applied the rule-update pattern at least once: triggered a mistake, diagnosed the missing rule, added it, and verified the correction.
3. The project has a `constraints.md` with at least 5 negative constraints, each paired with an alternative action, linked from CLAUDE.md.
4. You have built, documented, and installed one reusable Skill.
5. You have completed the quality checklist below.

---

## Part 1 - Initialize and Author CLAUDE.md

### Step 1: Run `/init`

Start Claude Code in the starter project directory, then run the `/init` slash command at the prompt:

```
> /init
```

`/init` inspects the project and writes a CLAUDE.md scaffold. Review what it produced. The starter already contains a deliberately weak CLAUDE.md, so `/init` will be working against an existing file - keep what's accurate, remove what's not, and get ready to replace the vague rules.

> Slash commands are a volatile layer - they change between Claude Code releases. If `/init` isn't available in your version, run `/help` to see what is, or just write CLAUDE.md by hand. Same result; the scaffold is a convenience, not the lesson.

### Step 2: Author your CLAUDE.md

Using the template below, add project-specific rules for the Document Analyzer. Aim for 10-15 rules. Every rule should be specific and actionable - something a literal-minded agent can follow without ambiguity.

**Template** (adapt every section to the project):

```markdown
# CLAUDE.md

## Project Overview
[One paragraph: what this project does, who uses it, what problem it solves]

## Stack
- Python [version]
- [Framework] for [purpose]
- [Key libraries with versions where it matters]

## Coding Conventions
- Use type hints on all function signatures
- Use [naming convention] for [what]
- Import ordering: stdlib → third-party → local, separated by blank lines
- Use [logging library] configured in [path] - do not use print() for logging
- Error handling: [your convention - e.g., raise specific exceptions, don't catch bare Exception]

## Testing
- Use [framework] for all tests
- Test files live in [directory] with [naming convention]
- Use [fixtures/mocking strategy]
- Minimum coverage expectation: [percentage or "all public functions"]

## Production Constraints
- Deployment target: [e.g., Vercel + Supabase, AWS Lambda, Docker]
- Environment variables: stored in .env (never committed), loaded via [method]
- Secrets: [how handled - e.g., never hardcoded, use env vars or secrets manager]
- [Any security requirements relevant to the project]
```

**Good rules vs. bad rules:**

| Bad (too vague) | Good (specific and actionable) |
|---|---|
| Write clean code | Use type hints on all function signatures. Use `snake_case` for functions and variables, `PascalCase` for classes. |
| Use proper testing | Use pytest for all tests. Place test files in `tests/` with `test_` prefix. Use fixtures for setup - do not use `setUp`/`tearDown` methods. |
| Handle errors correctly | Raise specific exceptions (`ValueError`, `NotFoundError`). Never catch bare `Exception`. Log errors with `structlog` before re-raising. |
| Keep it secure | Never hardcode secrets. Load from environment variables via `python-dotenv`. Never commit `.env` files. |

### Step 3: See for yourself it loads

Start a new Claude Code session in the project directory. Make a simple 11request (e.g., "What testing framework does this project use?"). Claude should answer based on your CLAUDE.md rules - not guess.

---

## Part 2 - The Rule-Update Pattern

The rule-update pattern: when Claude makes a mistake, don't just fix the output - add a rule to CLAUDE.md that prevents the same class of error in future sessions.

### Step 4: Trigger and diagnose

Make a Claude Code request that exercises one of your conventions. The starter's `tests/test_analyzer.py` uses `unittest` - a perfect trigger. Good candidates:

- "Write a test for [function in `src/analyzer.py`]" - does Claude use your testing framework and conventions?
- "Add error handling to [function]" - does Claude follow your error handling style?
- "Create a new module for [feature]" - does Claude follow your project structure?
- "Add a dependency for [task]" - does Claude check compatibility and document the addition?

### Step 5: Evaluate

Check Claude's output against your CLAUDE.md:
- Did Claude follow every relevant rule?
- If not - is the rule missing? Or is it too vague for a literal-minded agent to follow?

### Step 6: Update and verify

Add or improve the rule in CLAUDE.md. Be specific: state what to do AND what not to do.

Example improvement:
- Before: `Use pytest for testing.`
- After: `Use pytest for all tests. Do not use unittest.TestCase. Use pytest fixtures for setup and teardown - do not use setUp/tearDown methods. Place test files in tests/ with test_ prefix.`

Make the same request again. Verify Claude now follows the updated rule.

### Step 7: Document the cycle

In your homework notes (or a comment in CLAUDE.md), record:
- What mistake Claude made
- What rule was missing or insufficient
- What you added
- How you verified the fix

This write-up is part of the deliverable - you'll summarize it in the "What I Learned" section.

---

## Part 3 - Create constraints.md

### Step 8: Create the file

Create `constraints.md` in the project root. Every constraint follows this format:

```
**Don't [action].**
→ Instead, [alternative action].
```

### Step 9: Write 5+ constraints

Write at least 5 negative constraints relevant to the project. Each must have an alternative.

**Starter constraints for Python AI projects** (adapt to the project):

1. **Don't create new files unless explicitly asked.**
   → Instead, add content to existing files or ask which file to create.

2. **Don't install new dependencies without stating the reason and license.**
   → Instead, explain why the dependency is needed and confirm before running `uv add`.

3. **Don't use `print()` for debugging or logging.**
   → Instead, use the configured logging library (see CLAUDE.md for the logger path).

4. **Don't write tests that depend on external services or network calls.**
   → Instead, mock external calls with pytest fixtures or use recorded responses.

5. **Don't modify `.env`, configuration files, or CI workflows unless asked.**
   → Instead, propose the change and wait for approval.

6. **Don't refactor existing code while implementing a new feature.**
   → Instead, complete the feature first, then propose refactoring as a separate change.

7. **Don't add type: ignore comments to suppress type checker warnings.**
   → Instead, fix the type annotation or explain why the suppression is necessary.

### Step 10: Link from CLAUDE.md

Add a reference in your CLAUDE.md:

```markdown
## Read These Files
- @constraints.md
```

### Step 11: Test a constraint

Make a Claude Code request that would normally trigger the constrained behavior. For example, if you have a "don't create new files" constraint, ask Claude to implement something and see if it asks before creating files. If the constraint doesn't hold, make it more specific.

---

## Part 4 - Build a Skill

### Step 12: Choose a workflow

Pick a development workflow you perform repeatedly. Good candidates for AI engineering projects:

- **Code review** - Check code against project conventions, security patterns, and test coverage.
- **Test scaffolding** - Generate test stubs from a module's public API with correct fixtures and assertions.
- **Debug investigation** - Systematic approach to diagnosing a failing test or unexpected behavior.
- **Dependency audit** - Review a new dependency for license, security, maintenance status, and alternatives.
- **API endpoint scaffold** - Generate a FastAPI endpoint with validation, error handling, and tests following project patterns.

### Step 13: Create the Skill file

Create a Skill file. The file needs:

- **Name:** Short, descriptive (e.g., `code-review`, `test-scaffold`)
- **Description:** One sentence explaining when to use it
- **Trigger conditions:** When should Claude load this Skill?
- **Step-by-step instructions:** What Claude should do when the Skill is invoked

Example structure:

```markdown
---
name: code-review
description: Review code changes against project conventions, security patterns, and test coverage
---

When reviewing code, follow these steps:

1. Read the changed files and identify the scope of the change.
2. Check against CLAUDE.md coding conventions - flag any violations.
3. Check for security issues: hardcoded secrets, SQL injection, unvalidated input.
4. Verify test coverage: are new functions tested? Do existing tests still pass?
5. Check error handling: are exceptions specific? Is logging present?
6. Report findings as: [PASS], [WARN], or [FAIL] with file:line references.
```

### Step 14: Install and test

Install your Skill following the current Claude Code installation mechanism. Then invoke it on the starter project to verify it works as expected.

If the Skill produces output that isn't useful, revise the instructions - this is the same rule-update pattern applied to Skills.

---

## Quality Checklist (Best Practices Ownership)

Evaluate your own work. Check every box honestly - unchecked items are what you improve next.

- [x] My CLAUDE.md has ≥10 specific, actionable rules (not vague advice like "write clean code").
- [x] My CLAUDE.md follows the 100-150 instruction ceiling - concise and operational, not documentation.
- [x] I applied the rule-update pattern at least once and can explain the mistake, the rule, and the fix.
- [x] My constraints.md has ≥5 constraints, each with an alternative action.
- [x] My Skill has clear documentation: what it does, when to use it, and what it produces.
- [x] I can explain the difference between CLAUDE.md (always loaded), Skills (on-demand), and agents (autonomous).

---

## What I Learned

Write 3-6 bullets in your own words:

- One rule you added and the specific mistake it prevents (if you can't name the mistake, the rule is too vague).
  The rule "All imports at the top of the file, never inside functions or classes" prevents the mistake of inline imports like def test(): from pathlib 
  import Path, which hides dependencies and violates Python conventions.
- The rule-update pattern in your own words - what mistake you triggered, what rule fixed it, how you verified.
 I triggered the mistake by importing inside a function, diagnosed that the original vague rule didn't forbid it, updated the rule to be explicit with
  examples, and verified by making the same CSV test request again—Claude correctly placed all imports at the top.
- Why one of your Skills is a Skill and not a CLAUDE.md rule - what would happen if you put it in CLAUDE.md instead.
If the 6-phase code-review workflow were in CLAUDE.md, the file would balloon to 500+ lines and Claude would try to follow it on every request instead
  of only when invoked with /code-review.
- One thing you'll carry into your capstone's CLAUDE.md once it has code.
The rule-update pattern itself—rules get better by triggering mistakes, diagnosing gaps, making rules explicit with examples, and verifying they work.

---

## Stretch Goals

For participants who finish early:

1. **Path-specific CLAUDE.md:** Create `tests/CLAUDE.md` with test-specific conventions that augment the root file. Verify Claude applies both when working in the `tests/` directory.

2. **Skill exchange:** Build a second Skill and share it with another participant. Install each other's Skills. Evaluate for: reusability (would it work on a different project?), documentation quality (could someone use it without asking you?), and specificity (does it actually change Claude's behavior?).

3. **Constraint audit:** Review your constraints.md against common agent failure modes - the Eager Editor (producing unrequested artifacts) and Pattern Breaker (inventing new structures). Add any patterns you missed.

---

## Capstone Connection

The starter now has persistent context that every future Claude Code session will use - and you've practiced building each layer:

- **CLAUDE.md** prevents repeated mistakes - Claude knows the conventions from the first request.
- **constraints.md** prevents agent overreach - Claude won't create files, install dependencies, or modify configs without asking.
- **Your Skill** automates a recurring workflow - invoke it whenever you need that capability.

As your capstone grows in later modules, you'll bring this same layer to it. In Lesson 3, you'll add Plan Mode for complex multi-step tasks - and a good CLAUDE.md makes those plans more accurate, because Claude already knows the project's conventions, testing requirements, and production constraints.