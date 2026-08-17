# Homework - Session Management and Context Rot

**Module:** M2 - Context Engineering & Claude Code
**Lesson:** 4 of 4
**Audience:** AI Engineer (developer track)
**Format:** Homework — worked top to bottom. Due before the next meeting.
**Prereqs:** Claude Code installed with a working API key. The Lesson 2 starter project (Document Analyzer) with the CLAUDE.md, constraints.md, and Skill you built in that homework.

> **This is homework.** The meeting was lecture and a live demo; here you practice the session-management moves yourself. Work top to bottom — later parts build on earlier ones.

## Context

You have built a Claude Code setup: CLAUDE.md with precise rules, constraints.md, a custom Skill, Plan Mode discipline, and a model-routing strategy. None of that helps if Claude stops applying it partway through a session.

Context rot is the failure mode where output quality degrades as context accumulates - not because the window fills up, but because attention spreads across too many tokens. Your CLAUDE.md rules are still in the system prompt; they are just competing with everything else you have loaded.

**A word on what this homework does and does not ask of you.** You cannot schedule context rot. Whether it shows up in a given session depends on the model, the window size, how many topics you switched between, and - usually the biggest factor - how much raw tool output and file content landed in your context. It might bite after five requests. It might not bite after a hundred. Nobody can predict it for your session, and this homework will not pretend otherwise.

So you are not being asked to reproduce degradation on demand. You are being asked to do two things that *are* under your control:

1. **Practice the recovery moves cold**, before you need them. Every part below is verifiable regardless of whether your output ever degrades - you can always read `/context`, you can always check whether a compacted fact survived, you can always confirm `/rewind` rolled the transcript back.
2. **Learn to recognize the symptoms**, and set up a log so that when rot does hit you - in M3, in your capstone, at work - you catch it instead of blaming the model.

The measurable thing is context *growth and composition*. The unpredictable thing is when that growth starts costing you quality. Measure the first; be ready for the second.

---

## Success Criteria

You're done when:

1. You have recorded `/context` readings from the start and end of a working session and can name what consumed the most window.
2. You have executed a proactive `/compact` with explicit Keep/Summarize/Discard instructions, verified a named fact survived, and compared the result against a vague instruction.
3. You have a reusable session-briefing template committed to the project.
4. You have used `/rewind` to abandon a bad path instead of fixing forward, and confirmed the conversation rolled back - not just the files.
5. You have delegated a research task to a subagent and measured the context it kept out of your main session.
6. You have committed `docs/session-management.md` covering the four recovery patterns plus a symptom card.
7. You have started `docs/context-rot-log.md` as a standing log for the rest of the course.
8. You have completed the quality checklist below.

Work in the **Lesson 2 starter project**. It already has a CLAUDE.md with specific, checkable rules, real source under `src/`, and tests - which is exactly what you need to have something to inspect, something to break, and rules to check adherence against. You will carry these practices to your capstone in later modules.

Commit a checkpoint before you start:

```bash
git add -A && git commit -m "checkpoint: before session-management homework"
```

---

## Part 1 - Read the Instrument Panel

Before you can manage context, you need to see it. Four commands are your instrument panel. Verify them against your Claude Code version - slash commands change between releases.

- **`/context`** - what is actually consuming your window right now, broken down by component (system prompt, CLAUDE.md, tool results, conversation, files).
- **`/cost`** or **`/usage`** - what the session has spent so far.
- **`/compact`** - summarize and continue.
- **`/clear`** - full reset; CLAUDE.md and your files remain.

### Step 1: Take a baseline reading

Start a fresh Claude Code session in the starter project. Before making any request, run:

```
> /context
```

Record: total tokens used, percentage of window, and the breakdown by component. Note how much of it is your CLAUDE.md and constraints.md - that is your fixed overhead on every session.

25.1k/200k tokens (13%)
Estimated usage by category
     ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   ⛁ System prompt: 6.6k tokens (3.3%)
     ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   ⛁ System tools: 15.7k tokens (7.9%)
     ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   ⛁ Skills: 1.2k tokens (0.6%)
     ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   ⛁ Messages: 1.7k tokens (0.8%)
     ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   ⛶ Free space: 174.9k (87.4%)

### Step 2: Do a normal session's worth of work

Make a handful of requests, mixing types the way a real working session does. Suggestions - adapt to what the starter actually contains:

- Add type hints to a function in `src/`
- Ask a research question ("compare three Python libraries for X")
- Read through a module and ask for an explanation of how it works
- Refactor a different function
- Ask about deployment or packaging for this kind of project
- Write a test for the function from the first request

There is no target number of requests and no point at which something is supposed to happen. Work until it feels like a normal stretch of work.

### Step 3: Take a second reading

```
> /context
```

Record the same numbers.

### Step 4: Compare and document

In your homework notes, answer:

Context Usage
     ⛁ ⛁ ⛁ ⛀ ⛁   Haiku 4.5
     ⛁ ⛁ ⛶ ⛶ ⛶   claude-haiku-4-5-20251001
     ⛶ ⛶ ⛶ ⛶ ⛶   46.1k/200k tokens (23%)
     ⛶ ⛶ ⛶ ⛶ ⛶ 
     ⛶ ⛶ ⛶ ⛶ ⛶   Estimated usage by category
                 ⛁ System prompt: 6.6k tokens 
     (3.3%)
                 ⛁ System tools: 15.7k tokens
     (7.9%)
                 ⛁ Skills: 1.2k tokens (0.6%)
                 ⛁ Messages: 23.7k tokens (11.9%)
                 ⛶ Free space: 152.8k (76.4%)

- How much did total context grow, in tokens and as a percentage of the window? 
It went up 20 tokens and 10%
- **Which component grew the most?** This is the important one. It is usually the conversation - becuase tool results and file contents are consiedered conversation, even when you type little. A single large file read or a verbose command output can dwarf everything you typed.
The messages went up the most (the only one that went up) 
- Your CLAUDE.md is a fixed number of tokens. What share of the total window was it at the start, and what share at the end? That ratio is attention dilution made visible.
- Run `/cost`. What did the session cost? Would you have guessed that number?
Total cost:            $0.1446
It's not a lot but it's not just $0.0001

**What you are learning here:** the mechanism, not the symptom. You may well have seen no quality drop at all across those requests - that is a perfectly normal outcome and not a failed exercise. What you have measured is the thing that *causes* the symptom, and how fast it accumulates in ordinary work.

---

## Part 2 - Proactive Compact

`/compact` summarizes the conversation and continues. Left to itself, it optimizes for recency and volume - the newest, largest blocks survive. Your early architectural decisions are old and small, which makes them exactly what gets summarized away. Proactive compact means you decide instead.

### Step 5: Write explicit preservation instructions

Still in your session from Part 1, write instructions in this shape:

```
Keep: [the specific decisions and facts you will need next - name files and functions]
Summarize: [the conversation flow, intermediate exploration]
Discard: [research tangents, abandoned approaches, output you are done with]
```

Be concrete. "Keep the type hints we added to `src/analyzer.py` and the decision to use pytest fixtures" is a usable instruction. "Keep the important stuff" is not.

### Step 6: Execute and verify

```
> /compact Keep: ... Summarize: ... Discard: ...
```

Then run `/context` again - note how much the window dropped.

 ⛁ ⛀ ⛁ ⛁ ⛁ ⛁ ⛁ ⛶ ⛶ ⛶   claude-haiku-4-5-20251001
     ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   34.5k/200k tokens (17%)
     ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶      
     ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   Estimated usage by category
     ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   ⛁ System prompt: 6.6k tokens (3.3%)
     ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   ⛁ System tools: 15.7k tokens (7.9%)
     ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   ⛁ Skills: 1.2k tokens (0.6%)
     ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   ⛁ Messages: 11k tokens (5.5%)
     ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   ⛶ Free space: 165.5k (82.8%)

It went down 5% and 10K tokens

Now verify the preservation actually worked. Make a request that **depends on a fact you told it to keep**, and that would produce visibly wrong output if that fact were gone. Check the result.

It ran the old tests that were there before and they passed.
---

## Part 3 - Fresh Sessions and the Briefing Template

CLAUDE.md reloads automatically on every new session. That is your persistence layer, and it means starting fresh costs far less than developers instinctively assume. What CLAUDE.md does *not* carry is which files you are in and what you are trying to do right now - that is what a brief is for.

### Step 7: Start clean and brief properly

Start a new session. Re-run one of the more substantial requests from Part 1, this time with a proper brief:

- Do **not** restate your CLAUDE.md rules. They are already loaded; repeating them wastes the context you are trying to protect.
- Do name the relevant files: "The relevant files are `src/analyzer.py` and `tests/test_analyzer.py`."
- Do state the task and its boundary: what you want, and what should not change.
- Do carry forward any decision from the previous session that still applies.

### Step 8: Compare the readings

Run `/context` in the fresh session. Compare against your end-of-session reading from Part 1. You are working on the same task with a small fraction of the tokens.

Compare the outputs too. The fresh one may be better, or it may be indistinguishable - both are honest outcomes and neither invalidates the practice. The reliable win is the one on the instrument panel: same work, less context, lower cost, more headroom before dilution matters.

 ⎿  Context Usage
     ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁   Haiku 4.5
     ⛁ ⛀ ⛁ ⛁ ⛁ ⛶ ⛶ ⛶ ⛶ ⛶   claude-haiku-4-5-20251001
     ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   29.3k/200k tokens (15%)
     ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ 
     ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   Estimated usage by category
     ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   ⛁ System prompt: 6.6k tokens (3.3%)
     ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   ⛁ System tools: 15.8k tokens (7.9%)
     ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   ⛁ Skills: 1.2k tokens (0.6%)
     ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   ⛁ Messages: 5.8k tokens (2.9%)
     ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   ⛶ Free space: 170.6k (85.3%)
    
    Now it went down to 4K tokens higher than the original request.

### Step 9: Build the template

Write `docs/session-brief-template.md` in the starter project - the snippet you will actually paste at the top of new sessions. It should have slots for: relevant files, the specific task, constraints or boundaries, and decisions carried over from a previous session. Keep it short. A brief that takes five minutes to fill in will not get used.

---

## Part 4 - Rewind Instead of Fix-Forward

### Step 10: Confirm your checkpoint

```bash
git status
```

You committed at the start of this homework. Confirm you are clean, or commit again now.

### Step 11: Deliberately go down a bad path

Make a request you expect to break things. Good candidates in the starter:

- "Refactor the analyzer module to be fully async, and convert every call site."
- "Replace the current validation approach with a completely different one throughout."
- Any architectural change large enough to break the existing tests.

Accept the changes. Run the tests and watch them fail.

```bash
uv run pytest
```

(If they don't fail, pretend they do).

They fail!

### Step 12: Resist the fix

Do **not** ask Claude to fix the breakage. Fixing forward adds the broken code, the error traces, and every correction attempt to a context that is already carrying your real work. That is more noise, not less. 

Before you rewind, run `/context` and note the number.

⎿  Context Usage
     ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁   Haiku 4.5
     ⛁ ⛀ ⛀ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   claude-haiku-4-5-20251001
     ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   23.6k/200k tokens (12%)
     ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ 
     ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   Estimated usage by category
     ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   ⛁ System prompt: 6.6k tokens (3.3%)
     ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   ⛁ System tools: 15.8k tokens (7.9%)
     ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   ⛁ Skills: 1.2k tokens (0.6%)
     ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   ⛁ Messages: 8 tokens (0.0%)
     ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   ⛶ Free space: 176.4k (88.2%)

### Step 13: Rewind

```
> /rewind
```

(Or press `Esc` twice on an empty prompt.) Select the checkpoint from *before* the bad request and choose **Restore code and conversation**.

Now verify both halves of what that did:

- **Files:** `git status` is clean again, and the tests pass.
- **Conversation:** run `/context`. The transcript rolled back too - the broken code and error traces are gone from your window, not just from disk.

That second half is the entire point, and it is what a plain `git checkout -- .` cannot do. Git reverts the files and leaves every error token sitting in your context.

**The caveat:** `/rewind` tracks Claude's own file edits. It does not track changes made by bash commands - `rm`, `mv`, `sed`, a script you ran. Your git checkpoint is the backstop for those. Use `/rewind` to clean the context; use git when something outside Claude's edits changed your files.

### Step 14: Re-approach from clean

Go after the same goal properly - Plan Mode first:

```
> Plan how to [the same goal] without breaking the existing tests. Which functions change, and in what order?
```

Review the plan before implementing.

### Step 15: Document

- What was your `/context` reading before the rewind, and after?
- What specifically did restoring the *conversation* remove that a `git checkout` would have left behind?
- Describe the moment you wanted to fix forward. What made it tempting?

I have to admit that since I did this yesterday and today was a new session I wasn't able to rewind but I used git stash.

---

## Part 5 - Delegate Noisy Work to a Subagent

Some tasks are inherently high-volume and low-density: comparing libraries, reading documentation, surveying approaches. Thousands of tokens of exploration for a conclusion you could write in a paragraph. A subagent does that work in its own context and returns only the result.

### Step 16: Pick a genuinely noisy task

Something research-heavy and relevant to the starter or your capstone:

- "Which Python library best fits [a real need in the project]?"
- "What are the current best practices for [error handling / config management / packaging] in this kind of project?"
- Anything requiring comparison across several options or reading external docs.

### Step 17: Measure, delegate, measure

1. Run `/context` and note the reading.

  Context Usage
     ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁   Haiku 4.5
     ⛁ ⛀ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁   claude-haiku-4-5-20251001
     ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁   70k/200k tokens (35%)
2. Delegate the task to a subagent (Claude Code's Agent tool - ask Claude to investigate it in a subagent if you are unsure of the invocation).
3. Take the result into your main session. Do not paste the research process, only the conclusion you will act on.
4. Run `/context` again.

  Context Usage
     ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁   Haiku 4.5
     ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁   claude-haiku-4-5-20251001
     ⛁ ⛁ ⛁ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   46.5k/200k tokens (23%)

### Step 18: Document

- What did you delegate, and what came back?
I delegated a subagent to research about Error handling in this project and it created an error-handling-guilde.py and error-handling-guide.md
- How much did your main session's context grow - just the returned result?

  ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁   Haiku 4.5
     ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁   claude-haiku-4-5-20251001
     ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁   59.5k/200k tokens (30%)

     went up 13K tokens
- Estimate what the same research would have cost inline. If you want the real number rather than an estimate, run the same question directly in a throwaway session and read `/context` there.

⎿  Context Usage
     ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁   Haiku 4.5
     ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛀ ⛶ ⛶ ⛶   claude-haiku-4-5-20251001
     ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   32.2k/200k tokens (16%)

      Context Usage
     ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁   Haiku 4.5
     ⛁ ⛁ ⛁ ⛁ ⛁ ⛀ ⛁ ⛁ ⛁ ⛁   claude-haiku-4-5-20251001
     ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁ ⛁   58.3k/200k tokens (29%)
     ⛁ ⛁ ⛁ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶
     ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   Estimated usage by category

     Went up 26K tokens instead of 13K 
- Rule of thumb to evaluate against: if a task will generate more than ~2,000 tokens of exploration for a result you can state in ~200, delegate it. Did your task clear that bar?
YES!

---

## Part 6 - The Session-Management Playbook

Create `docs/session-management.md` in the starter project. This is the deliverable you will actually reuse - write it for yourself six months from now, not for a grader.

Done

### Step 19: The symptom card

Open the playbook with the symptoms, because recognizing them is the part you cannot practice on a schedule. When any of these show up, suspect context rot before you blame the model:

- Claude ignores a CLAUDE.md rule it was following earlier in the same session.
- Output goes generic - it could be for any project, and has lost your naming, your structure, your conventions.
- Claude references a decision, file, or conversation that never happened.
- Claude re-asks for information you already gave it.

Add to the card, in your own words:

- **Your first diagnostic move.** (`/context` - and what you are looking for in the breakdown.)
- **The distinction that matters:** rot is attention dilution, not a full window. If `/context` shows you at 12% and quality has dropped, "I ran out of space" is not the explanation. Do not wait for a full window to act.
- **Your personal tell** - once you have one. Leave the slot open until you do.

Added to Session-management.md
### Step 20: The four patterns

For each, write when *you* would reach for it in this project - specific triggers, not restated definitions:

**Fresh session / `/clear`** - What are the natural task boundaries in your work? What goes in the brief? (Point at your template from Part 3.)

- Starting a new feature (adding PDF/DOCX support, implementing batch processing)
- Switching from implementation to testing/debugging mode

**Proactive compact** - What is always in your "Keep" list? When is compact enough versus when do you want a clean start? What is your standard Keep/Summarize/Discard skeleton? 
- The current function being edited (name, signature, what it does)
- Test classes you wrote (names, what they cover)
- Coverage number we're targeting (≥85%)
- Any decision about architecture

**Rewind** - What tells you to rewind rather than fix forward? When is `/rewind` right (clean the conversation too) versus git (bash-driven changes, or a durable checkpoint)? How often do you commit before risky changes?

- Accepted a refactoring request that broke 5+ tests, and I can see the breakage is systemic (not a small fix)
- Loaded a large file that ate 20k tokens and the task I needed it for is now irrelevant
- Went down a dead-end architecture

**Subagent delegation** - Which kinds of work in this project are high-volume and low-density? What is your threshold for delegating rather than doing it inline?
High-volume, low-density work in this project:
- Comparing PDF parsing libraries — hours of research, 200 words of decision
- "What are best practices for error handling in production document processing?" — surveys docs, returns a pattern you can apply
- Researching deployment options (Docker, AWS ECS integration) — lots of docs, one clear recommendation

Delegation threshold:
- If a task will generate >2,000 tokens of exploration for a result I can state in <300 words → delegate

### Step 21: Multi-session continuity

Two more sections:

- **Handing off across days or weeks:** what belongs in CLAUDE.md (durable, every session) versus what you brief per session (current, transient)?

These never change. They reload automatically on every new session.

- Coding conventions: Type hints, naming (snake_case/PascalCase), import ordering, logging with structlog
- Testing framework: pytest only, fixtures in conftest.py, ≥85% coverage requirement
- Stack and tools: Python 3.11+, python-docx, PyPDF2, structlog, pydantic
- Quality gates: No bare Exception catches, no print(), context managers for files
- Security: Never hardcode secrets, use .env only
- Constraints: "Don't refactor without explicit request", "Don't install dependencies without approval"
- File handling: UTF-8 with error handling, validate paths, never assume encoding
- Rule-update log: When a mistake surfaced a missing rule, document it here so future sessions learn from it

The Handoff Pattern

End of session (before closing):
1. Run /context and commit: git add -A && git commit -m "end of session: [what you accomplished]"
2. Write a one-line note in your brief template slot for next time: "Pick up where we left off: DOCX extraction is 80% done; still need to add edge-case tests for corrupted files"

- **Your session hygiene defaults:** when do you check `/context`? When do you check `/cost`? Make these habits you would actually keep.

Check /context at the beginning and after 4-5 requests; if Messages % is growing too fast or you're at 40%+, compact or start fresh.  End of sessio run /cost once.

### Step 21: Commit

```bash
git add docs/session-management.md docs/session-brief-template.md
git commit -m "add session-management playbook and briefing template"
```

---

## Part 7 - Start Your Context-Rot Field Log

**This part does not finish with the homework.** It is a standing assignment for the rest of the course.

You may have gone through everything above without once seeing quality degrade. Good - that means your sessions were well managed, or your task mix was gentle, or the model handled it. It does not mean the failure mode is not real. It means you cannot summon it to order, which is precisely why you practiced the recovery moves cold.

Rot tends to bite in the conditions this homework cannot manufacture: multi-hour sessions, large file reads, long command output, many topic switches, a long debugging slog. You will hit those in M3 and beyond.

### Step 22: Create the log

Create `docs/context-rot-log.md` with a header and this entry template:

```markdown
# Context Rot Field Log

## Entry: [date]

**What I was doing:** [task, roughly how long the session had been running]
**Symptom:** [which one from the card - be specific: which rule got dropped, what went generic]
**`/context` reading:** [total, % of window, biggest component]
**What it was NOT:** [confirm the window was not full - the % is the evidence]
**Recovery used:** [compact / fresh session / rewind / subagent]
**Did it work:** [yes/no, and what you would do differently]
```

Commit it:

```bash
git add docs/context-rot-log.md && git commit -m "start context-rot field log"
```

### Step 23: Log the first one you hit

Between now and the next module, when a session starts drifting, fill in an entry before you fix it. The `/context` reading is the part everyone skips and the part that matters - it is what separates "context rot" from "the model had a bad day."

Bring your first real entry to a later meeting. First-hand field reports from the group are worth more than any demo, because they come with the details that make the pattern recognizable: what the session looked like, what tipped you off, what the numbers said.

If you get through the module without a single entry, that is a legitimate result - say so. An honest empty log beats a manufactured one.

---

## Quality Checklist (Best Practices Ownership)

Check every box honestly - unchecked items are what you improve next.

- [x] I have `/context` readings from the start and end of a working session, and I can name which component grew most.
- [x] I can explain why context rot is attention dilution rather than a full window, and I know what number to check to tell them apart.
- [x] I ran a proactive compact with explicit Keep/Summarize/Discard, verified a named fact survived, and compared it against a vague instruction.
- [x] I have a session-briefing template I would actually paste, and it does not restate my CLAUDE.md.
- [ ] I used `/rewind` instead of fixing forward, and I verified the *conversation* rolled back - not just the files.
- [x ] I know the `/rewind` blind spot (bash-command changes) and what covers it.
- [x ] I delegated a research task to a subagent and can quantify the context it kept out of my main session.
- [x] My playbook gives specific triggers for all four patterns, not restated definitions.
- [x] My field log exists and I know what I am watching for.

**Explain it back:** for each of the four recovery patterns, answer in one sentence: "Why is this better than the alternative, in this specific situation?" If you cannot state the situation, you have memorized the pattern rather than learned it.

1. Compact
Why it's better: Context rot is happening but the window isn't full—you have headroom to recover by removing the noise without restarting entirely. Better than a fresh session because you don't lose your accumulated work; better than rewind because you don't know the exact failure point; better than subagent because the problem is local drift, not systemic contamination.

2. Fresh session (/clear)
Why it's better: The context is so tangled (competing rules, failed fixes layered on fixes, foundational assumptions broke) that surgical removal won't help—you need to start clean. Better than compact because the damage is systemic, not just accumulated drift; better than rewind because you don't know where it went wrong; better than subagent when you need to preserve your own thinking but need to dump the conversation baggage.

3. Rewind
Why it's better: You know the exact commit/state where things worked, and context rot happened after that specific point—you can go back surgically and resume from there without losing prior context. Better than compact when you have a known-good anchor point; better than fresh session because you preserve all the good work before the failure; better than subagent when you want precision, not isolation.

4. Subagent
Why it's better: Your context is too polluted to work reliably in, but you can afford the cost and isolation—delegate to a fresh agent with only what it needs. Better than compact when the problem is too deep for local repair; better than fresh session when you want to protect your own context while shedding the polluted thread; better than rewind when there's no good anchor point to return to.

---

## What I Learned

Write 3-6 bullets in your own words:

- The single biggest consumer of your context window, and whether it was what you expected.
Messages consumed the most. My window grew from 25.1k (13%) to 46.1k (23%) — a 20k token increase — and the Messages component grew from 1.7k to 23.7k, accounting for most growth.

- Why proactive compact beats letting it happen automatically - argued from what you actually observed in Part 2, not from the lecture.
I compacted with explicit Keep/Summarize/Discard instructions and recovered 11.6k tokens. Proactive compact lets you decide what matters, without this you can lose important architectural components

- What restoring the conversation bought you in Part 4 that reverting the files alone would not have.
I used git stash instead of /rewind in that session, so I didn't measure this directly — but I understand the principle. A git checkout -- . would have restored my files to clean, tests passing. However, my /context would still carry the failed refactoring request, error traces, debug attempts, and all the noise from the breakage. Months later, reviewing the transcript, I'd still see the bad path I had abandoned. /rewind with "Restore code and conversation" does both: files go back AND the broken attempt vanishes from my context window. For future sessions where I revisit that transcript, the noise is gone. 

- One habit from this lesson you will keep in M3, and the trigger that will remind you to do it.
Trigger: When Messages percentage starts growing visibly (you noticed it jumped from 0.8% to 11.9% in Part 1) or you hit 40%+ total window.

Habit: Check /context at the start and after every 4-5 requests. If the Messages % is climbing too fast or you're above 40%, proactive compact with explicit Keep/Summarize/Discard before quality starts slipping. Also: run /cost once at the end of each session so you know the real financial cost and can calibrate whether a fresh start or subagent is worth it.

- If you saw genuine quality degradation anywhere in this homework: what it looked like. If you did not: say so plainly, and note which conditions you think would surface it in your own work.

I did not see quality degradation. None of my work in Parts 1-5 showed Claude dropping rules, going generic, or forgetting context — which is the honest outcome. My sessions were short, focused, and well-managed from the start. The failure mode is real but unpredictable; it tends to surface in M3's longer debugging sessions, large file reads, and multi-hour slogs. 

---

## Stretch Goals

1. **Compaction sensitivity.** Compare three levels of preservation instruction on comparable sessions - vague, specific, and exhaustively over-specified. Over-specification has its own cost: you are re-injecting everything you meant to compress. Where is the sweet spot?

2. **Context budget.** Add up your fixed startup cost: CLAUDE.md + constraints.md + Skill metadata + a typical brief + the files you usually open. What percentage of the window is spent before you have asked for anything? Does that change what you think belongs in CLAUDE.md versus a per-session brief?

3. **Deliberately induce it.** Try to force degradation: read several large files into context, run verbose commands, switch topics repeatedly, then check a specific CLAUDE.md rule. Log the `/context` reading at which anything shifted - **or log that nothing did, along with how far you pushed it.** A well-documented negative result is a genuine contribution here, and if you get one, bring it to the next meeting.

4. **Compare across models.** Run the same accumulation against two models with different window sizes. Does the composition of the window differ? Does anything else?

---

## Capstone Connection

The starter project now carries a complete context-engineering layer, and you have practiced each piece:

- **CLAUDE.md + constraints.md** - persistent rules (Lessons 1-2)
- **Skills** - reusable workflows (Lesson 2)
- **Plan Mode + model routing** - task-level control (Lesson 3)
- **Session management** - keeping all of the above effective as context grows (today)

M2 is complete. In M3 (Python for AI Engineering) you build production AI code, and the sessions get longer - real debugging, real file reads, real research. That is where this lesson stops being theoretical. Your playbook is the thing you reach for, and your field log is where the first real entry goes.