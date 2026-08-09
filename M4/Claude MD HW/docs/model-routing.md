# Model Routing Strategy

This document captures deliberate decisions about which Claude model to use for different task categories in the Document Analyzer project. Each choice balances capability, cost, and task characteristics.

## Model-Selection Framework

For each task, evaluate three dimensions:

- **Complexity:** How much reasoning, planning, or architectural judgment does the task require?
- **Stakes:** What's the cost if the output is suboptimal? (e.g., rework, bugs, security issues)
- **Frequency:** How often does this task occur in typical development?

## Task Categories and Model Assignments

| Task Category | Model | Complexity | Stakes | Frequency | Reasoning |
|---|---|---|---|---|---|
| Complex architectural planning / refactoring | Opus 5 | High | High | Low | Architectural decisions shape the codebase for months. Opus's superior reasoning justifies the cost. Rare enough that speed isn't a bottleneck. |
| Everyday feature implementation | Sonnet 5 | Medium | Medium | High | Most development work. Sonnet is fast enough to not interrupt flow, capable enough for feature-scope reasoning (dependencies, edge cases, test design). Cost-efficient at high frequency. |
| Simple additions (docstrings, type hints, formatting) | Haiku 4.5 | Low | Low | High | Haiku excels at mechanical, well-defined tasks. Docstrings and type hints have low stakes (easy to fix) and happen frequently. Fast + cheap = good DX. |
| Code review / debugging | Opus 5 | Medium–High | High | Medium | Subtle bugs require deep analysis. Stakes are high (undetected bugs reach users). Opus's superior context window and reasoning reduce false negatives. |
| Test generation | Sonnet 5 | Medium | Medium | Medium | Tests need to cover edge cases thoughtfully but don't require architectural foresight. Sonnet is capable enough; test code is easy to iterate on if needed. Cost-balanced. |

## When to Override This Strategy

- **If a task is blocked:** Use a more capable model to unblock, then return to routine choice.
- **If you're learning:** Use a more capable model to learn from its reasoning; less capable models sacrifice explanations for speed.
- **If the task is ambiguous:** Complexity jumps when requirements are unclear. Escalate to a more capable model until scope is clear, then revert.
- **If cost matters:** On a budget, shift everything down one tier and accept longer iteration cycles.

## Notes on This Project

- **Haiku's fit:** Document Analyzer is relatively straightforward (no distributed systems, no complex ML). Haiku is capable enough for most tasks here.
- **Opus triggers:** Adding PDF/DOCX support (new format complexity) or a caching layer (interaction complexity) would warrant Opus planning.
- **Speed vs. capability:** Because the project is small and feedback loops are fast, trading capability for speed (Haiku on routine tasks) is a good trade. You'll catch issues quickly in tests.

## Review Cadence

Revisit this strategy when:
- The project scope changes significantly (e.g., adds batch processing, external APIs, or distributed features).
- You notice a task going badly wrong despite using the assigned model (signal: escalate).
- You hit a cost threshold and need to optimize (signal: shift down tiers where safe).
