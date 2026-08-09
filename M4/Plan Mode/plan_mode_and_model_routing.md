# Homework - Plan Mode and Model Routing

**Module:** M2 - Context Engineering & Claude Code
**Lesson:** 3 of 4
**Audience:** AI Engineer (developer track)
**Format:** Homework — worked top to bottom. Due before the next meeting.
**Prereqs:** Claude Code installed with a working API key. The Lesson 2 starter project (Document Analyzer) with the CLAUDE.md, constraints.md, and Skill you built in that homework.

> **This is homework.** The meeting was lecture and a live demo; here you drive Plan Mode yourself and commit a model-routing strategy. Work top to bottom — later parts build on earlier ones.

## Context

In Lesson 2 you gave Claude persistent context: a CLAUDE.md it reads every session, a constraints.md that bounds what it does unasked, and a Skill for a workflow you repeat. Claude now knows the project.

Knowing the project does not stop it from deciding things you never reviewed. Given a complex request, Claude Code's default is to start building - picking a library, choosing a pattern, structuring files, handling errors its own way - and hand you working code with fifteen decisions baked in. The code may be fine. You still didn't review the decisions.

Plan Mode is the checkpoint: Claude analyzes, writes a structured plan, and stops. You review the approach before any code exists. Model routing is the other half of the same discipline - matching the model's capability and cost to what the task actually needs, rather than defaulting.

You'll work on the **Lesson 2 starter project** (Document Analyzer), continuing from the CLAUDE.md and constraints.md you wrote there. A good CLAUDE.md makes plans more accurate, because Claude already knows the conventions it has to plan within - you'll see that directly. You'll bring both practices to your own capstone in later modules, once it has code.

Confirm you're set up before you start:

```bash
cd path/to/document-analyzer
git status          # clean, and it IS a repo (see the starter README if not)
uv run pytest       # six tests, all passing
```

---

## Success Criteria

You're done when:

1. You have documented what Claude assumed when you skipped Plan Mode (Phase A).
2. You have a Plan Mode plan that passes the quality checklist on at least 4 of 5 criteria (Phase C).
3. You have committed an approved `plan.md` to the starter project (Phase D).
4. You have documented a model-selection strategy covering at least 4 task categories (Phase E).
5. You have a working enforcement hook committed to the project, tested in both directions (Phase G).
6. You have completed the quality checklist below.

---

## Phase A - Experience the Failure Mode

This phase is deliberate productive friction. You will see why Plan Mode matters by working without it first.

1. Choose a non-trivial feature for the Document Analyzer - something that spans 2+ files or requires architectural decisions. Good candidates:

   - **File input.** A `src/readers.py` that loads `.txt` and `.md` documents from disk, validates size against `MAX_DOCUMENT_SIZE` from `get_config()`, and feeds `analyze_document()`. Touches a new module, `src/config.py`, and the tests.
   - **Batch analysis.** Analyze every document in a directory and return aggregated results, collecting per-file errors instead of failing the whole run on one bad file.
   - **A CLI entry point.** `python -m src` (or a `src/cli.py`) that takes a path and flags, reads defaults through `get_config()`, and prints results in the configured `OUTPUT_FORMAT`.
   - **Result caching.** Cache `analyze_document()` results keyed on document content, so re-analyzing the same text is free.

2. Submit the request to Claude Code WITHOUT invoking Plan Mode. Let it run.

3. Before accepting anything, examine what Claude produced. Document every assumption you can identify:
   - Library or package choices you didn't specify
   - Architectural patterns you didn't request (e.g., decorator, factory, singleton)
   - File structure decisions (new files, directory organization)
   - Error handling approaches
   - Naming conventions
   - Configuration assumptions (paths, size limits, output formats)
   - Scope decisions (features added or omitted beyond your request)

4. Write down at least 3 specific assumptions. For each, note whether you agree with the choice or not.

   1) it wants to create a config file with assumptions such as MAX_DOCUMENT_SIZE: int = 50 * 1024 * 1024  # 50MB
   2)  Added OUTPUT_FORMAT to config (unused)
    - The CLAUDE.md mentions "configured OUTPUT_FORMAT" but your request didn't ask for it. Claude added it preemptively.
    - Agree? No — unnecessary. Follow YAGNI: don't add configuration you haven't actually used yet.
   3) Used built-in FileNotFoundError instead of custom DocumentNotFoundError
    - The existing analyzer uses custom exceptions from src.exceptions. Claude raised the built-in FileNotFoundError instead of staying consistent with the project's pattern.
    - Should you agree? No — inconsistent. Should use DocumentNotFoundError to match the existing codebase conventions.

5. Reject all changes.

> **Worth noticing:** some assumptions Claude *didn't* have to make, because your CLAUDE.md already answered them - the test framework, the import ordering, whether to use `print()`. That's Lesson 2 paying off. The ones left are the ones Plan Mode is for.

---

## Phase B - Apply Plan Mode

1. Rewrite your request with more detail. Add:
   - Explicit scope: what the feature does and does not do.
   - Constraints: specific libraries, patterns, or conventions the project uses.
   - Edge cases you want handled (empty file, file too large, unreadable encoding, directory with no matching files).
   - Context about the existing structure Claude should respect - `src/analyzer.py`'s existing signatures, `get_config()`, the `AnalysisResult` shape.

2. Toggle Plan Mode: press `Shift+Tab`. Confirm the mode indicator shows "Plan."

3. Submit the improved request.

4. Read the plan Claude produces. Do not approve yet.

5. Compare: look at the assumptions from Phase A. How many are now visible in the plan? How many are absent?

 3 assumptions are now visible in the plan 

---

## Phase C - Evaluate Against the Quality Checklist

Apply these five criteria to the plan from Phase B:

- [ ] **Specific:** Steps concrete enough to implement without guessing? Vague steps like "add file reading" fail this criterion. Concrete steps like "add `read_document(path: Path) -> str` in `src/readers.py` that raises `ValueError` when the file exceeds `MAX_DOCUMENT_SIZE`" pass.

- [x] **Assumptions visible:** Gaps Claude filled are stated, not hidden? If the plan names a library, an encoding, or a design decision, it passes. If it jumps straight to implementation details without stating what it chose, it fails.

- [x] **Edge cases addressed:** Non-obvious conditions mentioned? Empty document, file larger than the configured limit, unreadable encoding, directory containing no matching files, path that doesn't exist?

- [x] **Understandable in a week:** Would future-you understand this plan without remembering today's session? Plans that reference "the thing we discussed" or assume context fail. Self-contained plans pass.

- [x] **Scope is right:** No scope creep (plan adds unrequested features) and no scope gaps (plan omits stated requirements)? Check it against your constraints.md while you're here - did the plan propose refactoring existing code you didn't ask it to touch?

### What to do with the result

| Checklist result | Action |
|---|---|
| 4-5 criteria pass | Proceed to Phase D. |
| 2-3 criteria pass | Improve your request: add a missing constraint, an edge case, or a clearer scope boundary. Re-run Plan Mode. |
| 0-1 criteria pass | Your request needs fundamental rework. Narrow the scope or split into smaller tasks. |

If you improve and re-run, document what you changed in your request and how the plan improved.

5 out of 5 criteria pass

---

## Phase D - Approve and Commit

1. Approve the plan. Let Claude implement it.

2. Review the implementation against the plan:
   - Does the code match what the plan specified?
   - Did Claude deviate from the plan? If so, is the deviation an improvement or a problem?
   - Do the existing six tests still pass? `uv run pytest`

3. Save the approved plan as `plan.md` in the project root. If you already have a `plan.md`, use `plans/plan-<feature-name>.md`.

4. Commit both the plan and the code:
   ```bash
   git add plan.md [changed files]
   git commit -m "feat: [description] (plan approved)"
   ```

5. Verify: open `plan.md` in your editor. Can someone who wasn't in this session understand what was built and why?

---

## Phase E - Model Selection Strategy

1. Create `docs/model-routing.md` in the project. (You'll be adding more to `docs/` in Lesson 4, so the directory earns its place.) A section in your CLAUDE.md also works if you'd rather keep it loaded every session - decide deliberately, and note why.

2. For each task category below, document which model you would use and why. Use the three-question framework (complexity, stakes, frequency) to justify each choice:

   | Task Category | Model | Complexity | Stakes | Frequency | Reasoning |
   |---|---|---|---|---|---|
   | Complex architectural planning / refactoring | | | | | |
   | Everyday feature implementation | | | | | |
   | Simple additions (docstrings, type hints, formatting) | | | | | |
   | Code review / debugging | | | | | |
   | Test generation | | | | | |

3. Try the `/model` command: switch to a different model than your default and run a simple task on the project (e.g., "add a docstring to `_compute_readability` in `src/analyzer.py`"). Observe the output quality and speed.

4. Commit your model-selection document:
   ```bash
   git add docs/model-routing.md  # or CLAUDE.md if you added a section there
   git commit -m "docs: add model-routing strategy"
   ```

---

## Phase F - Model Comparison (optional)

1. Choose a moderate-complexity task (not trivially simple, not deeply architectural). Converting `tests/test_analyzer.py` from `unittest` to pytest style is a good one if you haven't already.

2. Run the same request on two different models (e.g., Sonnet and Haiku, or Sonnet and Opus).

3. Compare:
   - **Output quality:** Is the more capable model noticeably better for this task?
   - **Response time:** How much faster is the cheaper model?
   - **Token consumption:** Check `/cost` for both requests.

4. Document your finding: when is the cheaper model sufficient? When is the premium model worth the cost?

---

## Phase G - Write an Enforcement Hook

CLAUDE.md and constraints.md are advice - the model interprets them, and interpretation can fail. A hook is enforcement: a shell command Claude Code runs automatically at a lifecycle point, whether or not the model remembers your rules.

The layering to keep straight: **CLAUDE.md advises. Permissions gate. Hooks enforce.**

> Hook event names and configuration format are a volatile layer - check the current Claude Code docs if the settings below don't match what you see.

1. Pick one rule from your `constraints.md` that would be genuinely dangerous if ignored. Good candidates: force-pushing, deleting files outside the project, editing your `.env` (which now holds real config for this project).

2. Write a pre-action hook that blocks it. In the project's `.claude/settings.json`, configure a `PreToolUse` hook for the `Bash` tool that inspects the command and exits non-zero (blocking the action) when it matches your dangerous pattern. A small Python or bash script checking for e.g. `push --force` / `push -f` is enough.

3. Test the gate both ways:
   - Ask Claude to do something that triggers your hook (e.g., "force-push this branch"). Confirm the action is blocked - not because the model declined, but because the hook rejected it.
   - Ask for a normal, safe operation and confirm the hook lets it through.

4. Commit the hook configuration alongside CLAUDE.md and constraints.md:
   ```bash
   git add .claude/settings.json [your hook script]
   git commit -m "add enforcement hook for [rule]"
   ```

5. Document in one paragraph: which rule did you promote from *advice* to *enforcement*, and why that one? What's the difference in guarantee?

---

## Quality Checklist (Best Practices Ownership)

Evaluate your own work. Check every box honestly - unchecked items are what you improve next.

- [ ] I documented at least 3 specific assumptions Claude made when I skipped Plan Mode.
- [ ] My plan passes at least 4 of 5 quality criteria.
- [ ] I improved my request at least once before the plan was acceptable (if the first plan was perfect, try a second feature to practice the improvement cycle).
- [ ] My committed `plan.md` is understandable without session context.
- [ ] My model-selection strategy covers at least 4 task categories with reasoning for each.
- [ ] I can explain the decision boundary: when to use Plan Mode vs. building directly. (The answer: task complexity and risk. Simple, unambiguous, low-risk tasks can skip Plan Mode. Everything else uses it.)
- [ ] My enforcement hook blocks the dangerous action and passes the safe one, and the configuration is committed.
- [ ] The existing test suite still passes after my Phase D implementation.

---

## What I Learned

Write 3-6 bullets in your own words:

- The most dangerous assumption Claude made in Phase A, and what it would have cost you to discover it later.
- What you changed between your Phase A request and your Phase B request - and which single change did the most for the plan's quality.
- One assumption Claude *didn't* have to make because your CLAUDE.md already answered it.
- The rule you promoted from advice to enforcement, and how you'd explain the difference in guarantee to a teammate.
- Where your model-routing strategy will actually change your behaviour, versus where you wrote down what you were already doing.

---

## Stretch Goals

- **Second plan:** Run Plan Mode on a different feature from the Phase A list. Compare the quality of your second plan to your first - did your request-writing improve?

- **Requirements change test:** Change one requirement in your approved plan (e.g., "now also support PDF input" or "documents can be 100x larger"). Ask Claude to update the plan. How much changes? Is the plan structured for changeability, or does one change cascade through every step?

- **Cost calculation:** Estimate the token cost of your Plan Mode session with `/cost`. Compare to what a direct (no-plan) session would have cost. Factor in the rework cost of wrong assumptions - is Plan Mode cheaper in total?

---

## Capstone Connection

The starter project now has:
- An approved implementation plan committed as a reviewable artifact (`plan.md`).
- A documented model-selection strategy that guides cost-conscious decisions for the rest of the course.
- An enforcement hook - the first rule you made impossible to break rather than merely inadvisable.
- Evidence of at least one Plan Mode improvement cycle.

**Keep this project.** Lesson 4 continues on it - and it now has more to work with: a feature you built, a plan, and a bigger test surface.

In Lesson 4, you'll learn to manage context across sessions - because complex plans often span multiple Claude Code sessions, and context rot degrades quality as sessions grow long. Before Lesson 4, identify the next feature you'd build on this project and write a Plan Mode request for it - don't run it yet. Bring the written request to Lesson 4.
