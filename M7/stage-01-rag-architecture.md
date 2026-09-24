# Stage 1 - RAG Architecture

**Lab:** RAG End-to-End Pipeline (M4 rolling lab)
**Stage:** 1 of 6 - assigned after Lesson 1 (RAG Architecture)
**Format:** Homework - worked top to bottom.
**Pattern:** B rolling lab stage

> **This is homework.** The Lesson 1 meeting was lecture and a live demo; here you build this stage yourself, on your own capstone. Work top to bottom - later parts build on earlier ones, and every stage builds on the one before it. Commit as you go: Stage 2 assumes everything here is committed and working.

## Context

You're starting a module that builds a complete RAG pipeline over six lessons. You are **not** starting a new project: the capstone you scaffolded in M3 is the project, and RAG is the next layer on top of it. This first stage adds the retrieval dependencies and package, then produces an architecture document that maps the decisions for everything you'll build next. The architecture choices you make here determine how the pipeline behaves at scale - choose deliberately, not quickly.

## Prerequisites

- Your M3 capstone project (`capstone-ai/`) with a committed `uv.lock`
- Anthropic API key (from M1), already in the project's `.env`
- Claude Code set up (M2)
- A document set for your capstone (at least 5 files - PDF, Markdown, plain text, or HTML)

## Steps

### Part A - Extend the Capstone for RAG

### Step 1: Open the capstone and confirm it is healthy

```bash
cd capstone-ai
uv sync --locked
```

`--locked` fails if `uv.lock` is out of date with `pyproject.toml` rather than silently re-resolving. If it fails, run `uv lock`, commit the result, and continue - you want a clean starting point before adding the RAG dependency set.

If you see `No pyproject.toml found` → you are in the wrong directory. Run `pwd` and `cd` into the capstone you built in M3.

### Step 2: Add the RAG dependencies

```bash
uv add "anthropic>=0.40.0" "chromadb>=0.5.0" "pinecone>=5.0.0" \
       "langchain-text-splitters>=1.0.0" "fastembed>=0.8.0" \
       "rank-bm25>=0.2.2" "pymupdf>=1.24.0"
```

`anthropic` and `python-dotenv` are already there from M3 - `uv add` on an existing dependency just re-resolves it, so listing `anthropic` again is harmless.

Note also what is **absent**. There is no `langchain` meta-package: this module uses
LangChain for text splitting only, and since LangChain 1.x that lives in the small
standalone `langchain-text-splitters` package - the monolith would add a large
dependency tree nothing here imports. And there is no `sentence-transformers` yet: on
Linux its default `torch` wheel is the CUDA build - roughly 2.7GB across 17 packages
that no M4 stage needs a GPU for. Local embedding in Stages 1-2 runs on `fastembed`
(ONNX, a couple hundred MB). Stage 3 adds `sentence-transformers` at the point the
cross-encoder work actually needs it, with a CPU-only torch pin.

Note what you did **not** do: there is no `requirements.txt` to hand-edit, and no separate install step. `uv add` writes the constraints into `pyproject.toml`, resolves the whole graph, updates `uv.lock`, and syncs your environment - one command, one source of truth. That is the M3 L1 lesson doing its job.

If `chromadb` fails with a build error → ensure you have a C compiler installed (`sudo apt install build-essential` on Ubuntu, or `xcode-select --install` on macOS).

### Step 3: Add the Pinecone key to your configuration

Append to `.env` (and to the committed `.env.example`, with a placeholder value):

```
PINECONE_API_KEY=your-key-here
```

Add the field to `src/capstone_ai/core/config.py` so it loads through `Settings` rather than a bare `os.environ` read:

```python
    pinecone_api_key: str = ""
```

Add `.chroma/` to `.gitignore` - the local vector index is a build artifact, rebuilt from your documents:

```
.chroma/
```

If your capstone documents are not yours to publish, add `data/documents/` too and commit a `data/documents/.gitkeep` so the directory still exists on a fresh clone.

### Step 4: Create the RAG package and document directory

```bash
mkdir -p src/capstone_ai/rag data/documents
touch src/capstone_ai/rag/__init__.py
```

This sits alongside the `api/`, `core/`, and `prompts/` packages from M3. Everything you build in this module lands in `rag/`, so the retrieval layer is one importable unit rather than files scattered at the project root.

Place your capstone document files (at least 5) into `data/documents/`.

### Step 5: Extend CLAUDE.md with RAG rules

Your capstone already has a `CLAUDE.md` from M2. **Add** a RAG section to it - don't start a new file:

- Stack decisions (Anthropic SDK, Chroma + Pinecone, LangChain for loading)
- Quality rules: "Always validate retrieval results before passing to generation," "Every pipeline stage must be independently testable," "Log chunk counts and token usage at each stage"
- Constraints: "Do not hardcode API keys," "Do not skip the embedding step by passing raw text to the LLM"

### Step 6: Write the first loader and verify it imports

Create `src/capstone_ai/rag/loader.py` with a minimal document loader that reads files from `data/documents/` and prints the raw text of each. Use Python's built-in file reading for `.txt` and `.md` files. Verify it runs:

```bash
uv run python -c "from capstone_ai.rag.loader import load_documents; docs = load_documents('data/documents'); print(f'Loaded {len(docs)} documents')"
```

You should see the count of loaded documents and their text printed.

Notice the **import** resolves from any directory inside the project, because `capstone_ai` is an installed package rather than a folder that happens to sit next to you. That is the src layout from M3 L1 paying off - a flat `src/loader.py` imported as `from src.loader import ...` only works when your shell happens to be in the right place. (The `'data/documents'` argument is still a path relative to your shell, so run this one from the project root.)

### Part B - Architecture Design

### Step 7: Research RAG architectures with Claude Code

Use Claude Code as a research partner. Ask it to compare naive RAG, advanced RAG, and modular RAG architectures for your capstone's use case. Review its analysis critically - don't accept the first recommendation without understanding the tradeoffs.

### Up to here!!! 9/22/2026

### Step 8: Create docs/architecture.md

Write `docs/architecture.md` (create `docs/` if it does not exist yet). Include:

1. **System diagram** - An ASCII or Mermaid diagram showing all 5 RAG pipeline stages (document loading → chunking → embedding → retrieval → generation) with data flow arrows and technology choices at each stage.

2. **Component decisions** - For each stage, state which technology you chose and a one-sentence justification:
   - Document loading: which formats, which libraries
   - Chunking: initial strategy choice and target chunk size
   - Embedding: which model and why
   - Vector store: Chroma for dev, Pinecone for production - why both?
   - Generation: Anthropic Claude - which model, why

3. **Data flow** - Describe what data enters and exits each stage (raw files → text + metadata → chunks + metadata → vectors + metadata → ranked chunks → cited answer).

4. **Scale considerations** - What happens when your document corpus grows 10x? Which component becomes the bottleneck?

5. **Failure modes** - Identify at least three ways the pipeline could produce a bad answer (retrieval miss, chunk boundary splitting a key fact, hallucination despite context).

### Step 9: Commit the architecture

```bash
git add docs/architecture.md CLAUDE.md src/capstone_ai/rag/ .env.example .gitignore pyproject.toml uv.lock
git commit -m "stage-1: RAG dependencies, rag package, and architecture decisions"
```

`pyproject.toml` and `uv.lock` go in the **same commit**. A commit that adds a dependency to one but not the other is the stale-lockfile failure you'll meet again in M7's CI.

## Success Criteria - You're Done When...

- [x] `uv sync --locked` succeeds in the capstone after adding the RAG dependencies
- [x] `.env` is in `.gitignore` and contains both your Anthropic and Pinecone keys
- [x ] CLAUDE.md has a RAG section added to the M2 rules (not a second file)
- [x] Sample documents load and print their text without errors
- [x] `docs/architecture.md` contains a system diagram covering all 5 RAG stages
- [x] Each technology choice in the architecture has a one-sentence justification
- [x] At least three failure modes are identified in the architecture document

## Quality Checklist (Best Practices Ownership)

After completing the steps, evaluate your work against these criteria. For any "no," fix it and explain why it matters.

- [x] Every RAG dependency was added with `uv add` (not `uv pip install`), so `pyproject.toml` and `uv.lock` both know about it
- [x] `pyproject.toml` and `uv.lock` are committed together in one commit
- [x] `.env` is in `.gitignore` - secrets are never committed
- [x] CLAUDE.md is under 150 instructions and scoped to this project's needs
- [x] Architecture diagram covers all 5 RAG stages with data flow
- [x] Each technology choice has a one-sentence justification (not "because it's popular")
- [x] Failure modes are acknowledged - not just the happy path

## Explain It Back

After your project scaffold is working and architecture is documented, explain in writing (3-5 sentences):

1. Why you chose your specific embedding model and vector store combination

Embedding + vector store: voyage-3 because Anthropic has no first-party embedding endpoint and Voyage handles long conversational transcripts well; Chroma in dev because it runs in-process for free and makes stage testing practical, Pinecone in prod because AWS ECS containers are ephemeral and a local index dies on every restart.

2. What the most likely failure mode is for your capstone's document type

Most likely failure mode: A requirement and its later qualifier landing in separate chunks (my corpus has a real case — a 150-unit minimum amended 40 minutes later to 75 units each), which is dangerous because the consumer is a deployment step, so the wrong value ships cleanly with no error.

3. What would change in your architecture if your document corpus grew from 100 to 1,000,000 documents

At 1M documents: Retrieval precision becomes the bottleneck, so metadata filtering becomes a hard pre-filter rather than a ranking hint, reranking gets added, the index splits per-stage (API schema docs are a separate corpus from transcripts), and re-indexing becomes a planned migration rather than a minutes-long rebuild.

## Stretch Goals

- Add a cost estimate to the architecture document: approximate tokens per query, embedding cost per document, storage cost per 1,000 chunks
- Create a decision matrix comparing two vector DB options (Chroma vs Pinecone) across 5 criteria relevant to your capstone
- Diagram a modular RAG architecture where pipeline stages are independently deployable services

## Common Pitfalls and Recovery

| Pitfall | How to recognize it | How to recover |
|---|---|---|
| `chromadb` build failure | C compiler errors during `uv add` | Install build tools: `sudo apt install build-essential` (Ubuntu) or `xcode-select --install` (macOS) |
| Dependency added but missing on another machine | Works for you, `ModuleNotFoundError` for a teammate | You used `uv pip install`, which touches only the environment. Re-add with `uv add` and commit `pyproject.toml` + `uv.lock` |
| API key not loading | `AuthenticationError` when calling Anthropic | Verify `.env` has no quotes around values; verify the field exists on `Settings` in `core/config.py` |
| `ModuleNotFoundError: capstone_ai` | Import fails despite the file existing | Run commands with `uv run`, not a bare `python` - `uv run` uses the project environment where `capstone_ai` is installed |
| Architecture doc is too vague | Justifications say "it's the best" without specifics | State the tradeoff: "Chroma for dev because no server setup needed; Pinecone for production because managed scaling" |
| Skipping failure modes | Architecture only describes the happy path | Ask yourself: "What if retrieval returns nothing relevant? What if the document is a scanned PDF with no OCR?" |

## Capstone Connection

This stage *is* your capstone - there is no separate practice project to port over later:
- Your document set should be real documents from your capstone domain - not the sample set
- The architecture decisions should reflect your capstone's actual scale and requirements

After this stage, your capstone has: the RAG dependencies declared and locked, a `capstone_ai.rag` package ready to fill in, a CLAUDE.md extended with RAG rules, and `docs/architecture.md` mapping the full pipeline.

## Connection to Next Stage

Stage 2 builds the first two pipeline stages from your architecture: document loading (multi-format) and chunking (three strategies compared). The sample loader you wrote here is a starting point - Stage 2 expands it to handle PDF, HTML, and structured formats with proper metadata.

## What I Learned

Write 3-5 bullets in your own words and keep them with the stage (e.g. a `## What I Learned` section at the bottom of `docs/architecture.md`, or a homework-notes file):

- Walk through your architecture diagram in writing, as if for a colleague: for one component choice, answer "why this one?" - state the tradeoff you accepted, not just the benefit.
- What would you change first if your corpus grew 10x, and why that component?
- One decision you made with low confidence, and what evidence from a later stage would confirm or overturn it.
