# Stage 2 - Ingestion and Chunking

**Lab:** RAG End-to-End Pipeline (M4 rolling lab)
**Stage:** 2 of 6 - assigned after Lesson 2 (Ingestion and Chunking)
**Format:** Homework - worked top to bottom.
**Pattern:** B rolling lab stage

> **This is homework.** The Lesson 2 meeting was lecture and a live demo; here you build this stage yourself, on your own capstone. Work top to bottom - later parts build on earlier ones, and every stage builds on the one before it. Commit as you go: Stage 3 assumes everything here is committed and working.

## Context

Your capstone has the RAG dependencies and the `rag` package, and your architecture decisions are documented. Now you build the first two pipeline stages: loading documents from multiple formats and chunking them into retrieval-ready pieces. Chunking is where most RAG pipelines silently fail - a chunk that splits a key fact across two pieces produces garbage retrieval downstream. You'll implement three strategies and see where each breaks.

## Prerequisites

- Stage 1 complete: RAG dependencies added to the capstone, `capstone_ai.rag` package created, `.env` configured
- At least 5 documents in `data/documents/` including at least one PDF, one Markdown file, and one other format (HTML or plain text)
- Stage 1 sample loader functional

## Steps

### Part A - Document Loader

### Step 1: Build a multi-format document loader

Create or expand `src/capstone_ai/rag/loader.py` with a `DocumentLoader` class that handles:

- **PDF** - Use PyMuPDF (already in the project from Stage 1's `uv add`; the import is `import pymupdf`) to extract text page by page. Preserve page numbers in metadata. The legacy `import fitz` alias still resolves but prints a deprecation warning, and `fitz is pymupdf` is `False` — use the real name.
- **Markdown** - Read raw text. Preserve heading structure in metadata.
- **HTML** - Strip tags, extract text content. Preserve title/section headers in metadata.
- **Plain text** - Direct read.

Each loaded document should be represented as a dict (or dataclass) with:

```python
{
    "text": "the full extracted text",
    "metadata": {
        "source": "filename.pdf",
        "file_type": "pdf",
        "page_count": 12,        # PDF only
        "load_timestamp": "...",
        "title": "..."           # if extractable
    }
}
```

### Step 2: Test the loader on your document set

```bash
uv run python -c "
from capstone_ai.rag.loader import DocumentLoader
loader = DocumentLoader()
docs = loader.load_directory('data/documents')
for doc in docs:
    print(f'{doc[\"metadata\"][\"source\"]}: {len(doc[\"text\"])} chars, type={doc[\"metadata\"][\"file_type\"]}')
"
```

Verify: every document loads without errors. Check that PDF text extraction looks correct - inspect the first 200 characters of a PDF's extracted text for garbled content.

If PDF text is garbled → the PDF may be scanned/image-based. Note this as a known limitation in your architecture document. For this lab, use text-based PDFs.

### Step 3: Explain it back - document loader internals

Before proceeding, answer: What does PyMuPDF's `page.get_text()` actually do? What information is lost when you extract text from a PDF (tables, images, formatting)? If Claude Code helped you write the loader, identify one design choice it made and explain whether you'd keep it.

What page.get_text() does: A PDF stores glyphs positioned at x/y coordinates, not sentences — get_text() reconstructs reading order from that geometry by grouping glyphs into spans, lines, and blocks, which is why it returns nothing on scanned PDFs (no glyphs, just an image).

What's lost: Tables flatten into ambiguous line streams (row/column relationships vanish), images are dropped entirely, and formatting like bold and font size goes too — so unlike my Markdown path, I can't extract PDF headings into metadata, since heading-ness lived in the font size that got discarded.

Design choice I'd keep: Claude Code swapped page_texts (a full second copy of the document in metadata) for page_offsets (character positions) — right call, since metadata rides through to the vector store and would multiply across every chunk, though the tradeoff is offsets break silently if a later stage rewrites the text, so the chunker should resolve them to page numbers immediately.

### Part B - Chunking Comparison

### Step 4: Implement fixed-size chunking

Create `src/capstone_ai/rag/chunker.py` with a `Chunker` class. Implement fixed-size chunking:

```python
def chunk_fixed(self, text: str, chunk_size: int = 500, overlap: int = 100) -> list[dict]:
    # Split text into chunks of chunk_size characters with overlap
    ...
```

Each chunk should include:

```python
{
    "text": "chunk text here",
    "metadata": {
        "chunk_index": 0,
        "chunk_strategy": "fixed",
        "start_char": 0,
        "end_char": 500
    }
}
```

### Step 5: Implement recursive character chunking

Add recursive character chunking using LangChain's `RecursiveCharacterTextSplitter`:

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

def chunk_recursive(self, text: str, chunk_size: int = 500, overlap: int = 100) -> list[dict]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    ...
```

> **The import is `langchain_text_splitters`, not `langchain.text_splitter`.** LangChain 1.x
> moved text splitters into a standalone package: `uv add langchain-text-splitters`
> (hyphens to install, underscores to import). The old path raises `ModuleNotFoundError`,
> and installing `langchain` does not bring it back. Every tutorial, Stack Overflow answer,
> and LLM completion written before the 1.0 release will hand you the dead import — so if
> Claude Code generates `from langchain.text_splitter import ...`, that is the model
> reciting stale training data, and correcting it is your job, not its.

Before accepting Claude's implementation: explain what the `separators` parameter controls and why the order matters. What happens if you reverse the list?

separators is an ordered fallback chain from coarsest to finest boundary (paragraph → line → sentence → word → character) that the splitter tries in sequence until pieces fit under chunk_size; reversing it makes the always-succeeding "" match first, so every split lands mid-word and the semantic structure the list exists to preserve is destroyed.

Then check something the parameters do not advertise: print the average chunk size. You asked for 500; you will get noticeably less, because the splitter stops early at separator boundaries. `chunk_size` is a ceiling, not a target. Budget context accordingly.

Already measured this against the real corpus earlier: recursive chunking averaged 378 chars against a requested 500 (76%), with only 6.3% of chunks reaching the ceiling and 18.5% falling under half of it — confirming chunk_size behaves as a ceiling, not a target, so context budgeting should plan for roughly 75% of the configured value, not the full amount.

### Step 6: Run both strategies on the same document and compare

Pick one document that contains structured content (a table, code block, or multi-section layout). Run both strategies and produce a comparison:

```python
# For each strategy, report:
# - Total chunk count
# - Average / min / max chunk size (characters)
# - One example of a BAD chunk boundary (mid-sentence split, broken table, etc.)
```

Save the comparison to `reports/chunking_comparison.md`.

### Step 7: Find and fix a chunk boundary failure

Inspect the chunks from both strategies. Find at least one case where a chunk boundary splits important information (a sentence cut in half, a table row separated from its header, a code block broken). Document:

- The original text around the boundary
- Which strategy produced the bad split
- How you fixed it (adjusted parameters, added a custom separator, etc.)

### Part C - Semantic Chunking + Metadata

### Step 8: Implement semantic chunking

Add semantic chunking that uses sentence embeddings to detect topic boundaries:

```python
from fastembed import TextEmbedding

embedder = TextEmbedding("BAAI/bge-small-en-v1.5")

def chunk_semantic(self, text: str, threshold: float) -> list[dict]:
    # Split text into sentences (keep the terminal punctuation - see note below)
    # Embed each sentence, normalise to unit length so dot product == cosine similarity
    # Group consecutive sentences with high similarity
    # Split where similarity drops below threshold
    ...
```

`fastembed` is ONNX-based and pulls no `torch`, which keeps the install to a couple of hundred megabytes instead of a couple of gigabytes.

This previews the embedding concepts from Stage 3. You don't need to understand embeddings deeply yet - treat the similarity score as "how related are these sentences."

**Two things that will cost you time if you skip them:**

*Do not split with `text.split(". ")`.* It discards the period, collapses `?` and `!` into `.`, and forces you to glue a `.` back on when you rejoin — so your chunker silently rewrites the corpus it is supposed to be indexing. Split with `re.split(r"(?<=[.!?])\s+", text)`, which keeps the punctuation attached.

*Do not accept a threshold from a tutorial.* Thresholds are specific to the embedding model, and 0.5 is a number that circulates because it was reasonable for an older one. **Print the distribution first:**

```python
sims = [float(v[i] @ v[i - 1]) for i in range(1, len(v))]   # unit-normalised vectors
print(min(sims), sorted(sims)[len(sims) // 2], max(sims))
```

If your threshold sits below the minimum you get one chunk; above the maximum, one chunk per sentence. Pick from the distribution, then sweep a few values and look at the output. Note the direction: a split happens when similarity is **below** the threshold, so a *higher* threshold produces *more* chunks.

### Step 9: Design and attach a metadata schema

Every chunk produced by any strategy should carry unified metadata:

```python
{
    "text": "...",
    "metadata": {
        "source": "original_filename.pdf",
        "file_type": "pdf",
        "chunk_index": 3,
        "chunk_strategy": "recursive",
        "start_char": 1500,
        "end_char": 2000,
        "page_number": 2,          # if applicable
        "section_header": "...",    # if extractable
        "parent_doc_id": "...",     # links chunk to source document
    }
}
```

Merge document-level metadata (from the loader) with chunk-level metadata (from the chunker).

### Step 10: Compare all three strategies

Run all three chunking strategies on a complex document. Update `reports/chunking_comparison.md` with the three-way comparison including semantic chunking results.

### Step 11: Commit

```bash
git add src/capstone_ai/rag/loader.py src/capstone_ai/rag/chunker.py reports/
git commit -m "stage-2: multi-format loader and three chunking strategies"
```

## Success Criteria - You're Done When...

- [X] Document loader handles at least 3 file formats without crashing
- [X] All three chunking strategies (fixed, recursive, semantic) produce chunks from the same document
- [X] `reports/chunking_comparison.md` shows chunk count, size statistics, and at least one boundary failure for each strategy
- [X] At least one chunk boundary failure has been identified, documented, and fixed
- [X] Every chunk carries metadata linking it to its source document

## Quality Checklist (Best Practices Ownership)

- [ ] Document loader handles edge cases gracefully (empty file, unsupported format returns a clear error)
- [ ] Chunking preserves complete sentences (no mid-word splits in any strategy)
- [ ] Chunk sizes are within a target range appropriate for your chosen embedding model (check your model's actual limit - `bge-small-en-v1.5` takes 512 tokens, but Voyage models take 32,000 and OpenAI's take 8,191; the old "512 max" rule of thumb is out of date, and retrieval quality binds well before the limit does)
- [ ] Overlap is configured and you can articulate why you chose your overlap size
- [ ] Metadata includes source attribution sufficient for citation in generated answers
- [ ] At least one chunking failure was identified, documented, and fixed
- [ ] Chunking strategy is swappable without rewriting the loader - the `Chunker` class accepts any loaded document

# up to here 24/9/2026
## Explain It Back

After your pipeline is working, explain in writing (3-5 sentences):

1. Which chunking strategy produced the best results for your capstone's document type and why

Recursive chunking with the bare-heading merge worked best on my meeting notes and roadmaps, because it splits on paragraph and sentence breaks, while fixed-size cut words in half and semantic produced 2-character chunks like "3."; this ranking rests on boundary behavior, not a measured retrieval evaluation.

2. What information is lost at chunk boundaries that might matter for retrieval

Chunk boundaries lose the surrounding context, such as a requirement separated from its exception, a list separated from its heading, or a pronoun separated from what it refers to.

3. What would you change about your chunking strategy if your users primarily asked multi-paragraph analytical questions vs short factual lookups


For multi-paragraph analytical questions I would use larger chunks of about 1,000–1,500 characters or a parent/child setup that retrieves whole sections, and keep the current small chunks for short factual lookups.

## Stretch Goals

- Implement a custom chunking strategy optimized for a specific document type in your capstone (e.g., splitting legal contracts by clause, splitting API docs by endpoint)
- Add deduplication: detect and remove near-duplicate chunks that result from overlapping or repeated content
- Benchmark chunking throughput (documents/second) for each strategy on your full document set

## Common Pitfalls and Recovery

| Pitfall | How to recognize it | How to recover |
|---|---|---|
| `ModuleNotFoundError: No module named 'langchain.text_splitter'` | Raised on the recursive chunking import | Use `from langchain_text_splitters import RecursiveCharacterTextSplitter` and `uv add langchain-text-splitters`. The old path was removed in LangChain 1.x. |
| Semantic chunking returns exactly 1 chunk (or 1 per sentence) | Chunk count equals 1, or equals your sentence count | Your threshold is outside the model's similarity range. Print min/median/max of adjacent-sentence similarity and choose from inside it. |
| PDF extracts garbled text | Output contains `\x00`, random characters, or no text | The PDF is likely image-based (scanned). Use a text-based PDF for the lab. Note OCR as a production consideration. |
| PDF text is clean but the table is meaningless | Values appear one per line with headers detached | Expected — extraction preserves characters, not structure. Record it as a known limitation, or handle tables separately. This is not a bug to fix in the loader. |
| Fixed-size chunks split mid-word | Chunks end with partial words like `"the implementa"` | Increase chunk size or add word-boundary detection to the splitter |
| Semantic chunking is slow | Takes >30 seconds for a single document | Reduce the document size for testing. Semantic chunking embeds every sentence - it scales linearly. |
| Metadata is lost between loader and chunker | Chunks have chunk-level metadata but no source info | Merge document metadata into each chunk's metadata dict in the chunking step |
| Recursive splitter produces tiny chunks | Many chunks under 50 characters | Adjust `chunk_size` upward or set a minimum chunk size filter |

## Capstone Connection

Now apply this to your capstone:
- Replace sample documents with your capstone's real document set
- Choose the chunking strategy that best fits your domain (the comparison report should inform this)
- Ensure metadata preserves enough source information for citation (users will want to know WHERE an answer came from)

After this stage, your capstone has: a working ingestion pipeline that loads domain documents, chunks them with a justified strategy, and outputs clean, metadata-tagged chunks ready for embedding.

## Connection to Next Stage

Stage 3 takes these chunks and turns them into vectors. The quality of your chunks directly determines the quality of your embeddings - garbage chunks produce garbage vectors. Before moving on, verify your chunks are clean: no garbled text, no mid-sentence splits, metadata intact.

## What I Learned

Write 3-5 bullets in your own words (a good home is the bottom of `reports/chunking_comparison.md`):

- Your worst chunk boundary failure: which document, what got split across the boundary, and how you fixed it.
- What assumption about user queries drove your chunking strategy choice?
- What would break if your documents changed format tomorrow?
