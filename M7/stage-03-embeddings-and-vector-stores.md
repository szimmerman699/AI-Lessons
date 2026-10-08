# Stage 3 - Embeddings and Vector Stores

**Lab:** RAG End-to-End Pipeline (M4 rolling lab)
**Stage:** 3 of 6 - assigned after Lesson 3 (Embeddings and Vector Stores)
**Format:** Homework - worked top to bottom.
**Pattern:** B rolling lab stage

> **This is homework.** The Lesson 3 meeting was lecture and a live demo; here you build this stage yourself, on your own capstone. Work top to bottom - later parts build on earlier ones, and every stage builds on the one before it. Commit as you go: Stage 4 assumes everything here is committed and working.

## Context

Your ingestion pipeline produces clean, metadata-tagged chunks. Computers don't understand text - they understand numbers. This stage bridges the gap: you turn chunks into vectors (embeddings) that capture semantic meaning, store them in vector databases for fast similarity search, and make the storage backend swappable between local development (Chroma) and managed production (Pinecone).

## Prerequisites

- Working ingestion and chunking pipeline from Stage 2 producing metadata-tagged chunks
- `PINECONE_API_KEY` in `.env` (the field you added to `Settings` in Stage 1)
- Pinecone account (free starter tier) - sign up at pinecone.io if you haven't
- At least 20 chunks from your document set (run your Stage 2 pipeline if needed)

## Steps

### Step 0: Add sentence-transformers, with a CPU-only torch

Stage 1 deliberately left `sentence-transformers` out of the dependency set: on Linux
its default `torch` wheel is the CUDA build - roughly 2.7GB across 17 packages, for
work that needs no GPU. This stage is where the library earns its install (the
cross-encoder in Stage 4 also uses it), so add it now, pinned to the CPU torch index.

Append to `pyproject.toml`:

```toml
[[tool.uv.index]]
name = "pytorch-cpu"
url = "https://download.pytorch.org/whl/cpu"
explicit = true

[tool.uv.sources]
torch = { index = "pytorch-cpu" }
```

Then add **both** packages - `torch` must be declared directly, because
`[tool.uv.sources]` only pins dependencies your project declares itself; left
transitive (pulled in silently by `sentence-transformers`), torch resolves from PyPI
and you get the CUDA build anyway:

```bash
uv add torch "sentence-transformers>=3.0.0"
```

Verify the pin took: `grep -A2 'name = "torch"' uv.lock` should show
`source = { registry = "https://download.pytorch.org/whl/cpu" }`, and
`grep -c 'name = "nvidia-' uv.lock` should print `0`. If nvidia wheels appear, torch
is not a direct dependency or the `[tool.uv.sources]` block is misspelled - fix and
run `uv lock` again.

> Why not `--torch-backend=cpu`? That flag (and `UV_TORCH_BACKEND`) only applies to
> uv's pip interface, not to project commands like `uv add` and `uv run`. The index
> pin above is the project-level equivalent, and it lives in `pyproject.toml` where
> the whole team inherits it.

### Part A - Chroma Local

### Step 1: Create the embedding pipeline

Create `src/capstone_ai/rag/embedder.py` with an `EmbeddingPipeline` class:

```python
from sentence_transformers import SentenceTransformer

class EmbeddingPipeline:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name

    def embed_chunks(self, chunks: list[dict]) -> list[dict]:
        texts = [chunk["text"] for chunk in chunks]
        embeddings = self.model.encode(texts, batch_size=32, show_progress_bar=True)
        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding.tolist()
        return chunks
```

Start with `all-MiniLM-L6-v2` (384 dimensions, fast, good baseline). You'll compare with a second model in Part C.

### Step 2: Set up Chroma and index chunks

Create `src/capstone_ai/rag/vector_store.py` with a `VectorStoreBackend` base interface and a Chroma implementation:

```python
import chromadb

class ChromaBackend:
    def __init__(self, collection_name: str = "rag_chunks", persist_dir: str = ".chroma"):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def index(self, chunks: list[dict]) -> None:
        # Add chunks with embeddings and metadata to the collection
        ...

    def query(self, query_embedding: list[float], top_k: int = 5, filters: dict = None) -> list[dict]:
        # Query the collection and return top-k results with scores
        ...
```

Index your chunks and verify:

```bash
uv run python -c "
from capstone_ai.rag.loader import DocumentLoader
from capstone_ai.rag.chunker import Chunker
from capstone_ai.rag.embedder import EmbeddingPipeline
from capstone_ai.rag.vector_store import ChromaBackend

docs = DocumentLoader().load_directory('data/documents')
chunks = Chunker().chunk_recursive(docs[0]['text'])
chunks = EmbeddingPipeline().embed_chunks(chunks)
backend = ChromaBackend()
backend.index(chunks)
print(f'Indexed {len(chunks)} chunks')
"
```

### Step 3: Run test queries

Write 5 test queries relevant to your document set. For each query:

1. Embed the query using the same model
2. Query Chroma for the top-5 results
3. Print each result's text (first 100 chars), similarity score, and source metadata

Inspect the results. Are the top results actually relevant to the query? Note any surprising results (good or bad).

Yes, results are relevant to the documents.
### Step 4: Explain it back - HNSW intuition

Before proceeding, answer: How does Chroma find similar vectors without comparing your query against every single stored vector? Explain HNSW at the intuition level - you don't need the algorithm details. Think: "It builds a _____ so it can _____ instead of _____."

It builds a layered graph linking each vector to its neighbors so it can hop from point to nearby point toward the query instead of comparing against every stored vector.

### Part B - Pinecone Managed

### Step 5: Create a Pinecone index

```python
import os
from pinecone import Pinecone, ServerlessSpec

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
pc.create_index(
    name="rag-pipeline",
    dimension=384,  # must match your embedding model
    metric="cosine",
    spec=ServerlessSpec(cloud="aws", region="us-east-1")
)
index = pc.Index("rag-pipeline")  # the queryable handle - create_index only provisions
```

If the index already exists → skip `create_index`; `pc.Index("rag-pipeline")` returns the handle either way.

If you get a `dimension mismatch` error → your embedding model's output dimensions don't match the index configuration. Check your model's dimensions and recreate the index.

### Step 6: Add Pinecone as a second backend

Add a `PineconeBackend` class to `src/capstone_ai/rag/vector_store.py` that implements the same interface as `ChromaBackend`:

```python
class PineconeBackend:
    def __init__(self, index_name: str = "rag-pipeline"):
        ...

    def index(self, chunks: list[dict]) -> None:
        # Upsert vectors with metadata to Pinecone
        # Use batch upsert (100 vectors per batch)
        ...

    def query(self, query_embedding: list[float], top_k: int = 5, filters: dict = None) -> list[dict]:
        # Query Pinecone and return results
        # Note: Pinecone metadata filtering syntax differs from Chroma
        ...
```

Make the backend swappable via configuration:

```python
def get_backend(backend_type: str = "chroma") -> VectorStoreBackend:
    if backend_type == "chroma":
        return ChromaBackend()
    elif backend_type == "pinecone":
        return PineconeBackend()
```

### Step 7: Index in Pinecone and compare results

Index the same chunks in Pinecone. Run your 5 test queries against both backends. Document any differences in:

- Result ordering (do they return the same top-5?)
- Similarity scores (different backends may report scores differently)
- Metadata filtering behavior

Note: Pinecone metadata filtering uses a different syntax than Chroma. Don't copy-paste your Chroma filter code - read the Pinecone docs and adapt.

### Part C - Model Comparison + Metadata Filtering

### Step 8: Switch embedding models

Choose a second embedding model. Options:

- `all-mpnet-base-v2` (768 dimensions, higher quality, slower)
- OpenAI `text-embedding-3-small` (1536 dimensions, API-based, costs per token)

Re-embed a sample of your chunks (at least 20) with the second model. If switching to a model with different dimensions, you'll need a separate Chroma collection or Pinecone index.

They both gave me the same results. And they were mixing things up from different files, so I'm putting in "source" markers.


### Step 9: Compare nearest-neighbor quality

For each of your 5 test queries, compare the top-5 results from both embedding models. Create `reports/embedding_comparison.md`:
 up
- Which model returned more relevant results for each query?

bge-small on 3 of 5 queries (Ad Infinitum, WordPress checkout, Dvar Torah), roughly a tie on Our Kehila, and mixed on consultation pricing. Its clearest win was the WordPress query, where all five results were checkout and plugin issues, while MiniLM spent two slots on fees.

- Did either model surface a result the other missed?

Results one model missed: overlap was low, 1–3 of 5 per query. The biggest case is the consultation query. bge returned three chunks from the "Schedule a Free Consultation" transcript, and MiniLM never returned that file. bge also found the roadmap's checkout-totals chunk, which MiniLM missed. MiniLM found Chaim's reaction to the rates, which bge missed.

- Note any domain-specific terms where one model performed better
Domain terms: bge-small did better on WordPress and e-commerce terms (price tables, cart quantity, checkout totals) and ranked community terms (rabbis, self-submission) higher. Both models match on speaker names and timestamps, which lets filler chunks like "Bye." and "Yeah." in, MiniLM more so.



up to here 5/1


### Step 10: Add metadata-filtered queries

Implement metadata-filtered queries in both backends. Examples:

- "Find chunks about X only from document Y" (filter by `source`)
- "Find chunks from page 3-5 of this PDF" (filter by `page_number`)

Verify that filters work correctly in both Chroma and Pinecone.

### Step 11: Commit

```bash
git add src/capstone_ai/rag/embedder.py src/capstone_ai/rag/vector_store.py reports/embedding_comparison.md
git commit -m "stage-3: embedding pipeline with dual vector store backends"
```

## Success Criteria - You're Done When...

- [ ] Chunks are indexed in both Chroma (local) and Pinecone (managed)
- [ ] You can switch between backends with a configuration change (not a code change)
- [ ] 5 test queries return results from both backends
- [ ] `reports/embedding_comparison.md` compares results from at least two embedding models
- [ ] Metadata-filtered queries work in both backends

## Quality Checklist (Best Practices Ownership)

- [ ] API keys are loaded from environment variables, never hardcoded
- [ ] Embedding model name is configurable, not hardcoded in the pipeline
- [ ] Batch embedding is used (not one-at-a-time calls) - check your `embed_chunks` method
- [ ] Vector store backend is swappable via a factory function or config parameter
- [ ] Metadata is preserved through the embedding pipeline (source, chunk strategy, page number all survive)
- [ ] Test queries cover both positive cases (relevant results expected) and at least one negative case (query about a topic not in the documents)
- [ ] Embedding dimensions match between model output and index configuration (384 for MiniLM, 768 for mpnet, 1536 for OpenAI)

## Explain It Back

After your dual-backend pipeline is working, explain in writing (3-5 sentences):

1. Why cosine similarity is used instead of Euclidean distance for text embeddings
2. What happens to your index if you change embedding models (can you query old vectors with a new model's embeddings?)
3. One difference you observed between Chroma and Pinecone's behavior on the same queries

## Stretch Goals

- Implement an embedding cache: hash each chunk's text, skip re-embedding unchanged chunks on subsequent runs
- Visualize your chunk embeddings in 2D using PCA or t-SNE (use `matplotlib`). Color-code by source document. Do semantically related chunks cluster together?
- Benchmark indexing throughput: chunks/second for Chroma vs Pinecone. Where's the bottleneck - embedding or storage?

## Common Pitfalls and Recovery

| Pitfall | How to recognize it | How to recover |
|---|---|---|
| Dimension mismatch | `ValueError: dimension mismatch` when indexing | Ensure embedding model dimensions match the index configuration. If you switch models, create a new index/collection. |
| Pinecone rate limiting | `429 Too Many Requests` | Use batch upsert (100 vectors per call). Add a small delay between batches on the free tier. |
| Metadata not surviving embedding | Chunks have embeddings but metadata is empty | Check that `embed_chunks` preserves the original metadata dict, not just adding the embedding field |
| Chroma and Pinecone return different scores | Scores don't match for the same query | This is expected. Chroma returns distance (lower = more similar), Pinecone returns similarity (higher = more similar). Normalize for comparison. |
| Slow embedding on CPU | Embedding 100+ chunks takes minutes | Use `batch_size=32` in `SentenceTransformer.encode()`. For OpenAI, batch API calls. |

## Capstone Connection

Now apply this to your capstone:
- Index your capstone's full document set (all chunks from Stage 2) in both backends
- Choose the embedding model that performs best on your domain's queries (the comparison report should inform this)
- Decide which backend is your development default and which is for production deployment

After this stage, your capstone has: all domain documents embedded and indexed in both Chroma and Pinecone, with the ability to switch between them via configuration.

## Connection to Next Stage

Stage 4 adds retrieval intelligence on top of your vector stores. You'll combine dense retrieval (what you just built) with sparse retrieval (BM25 keyword matching) into hybrid search, then add a reranker for precision. The quality of your embeddings directly determines retrieval quality - if your nearest-neighbor results look wrong, debug your embeddings before moving on.

## What I Learned

Write 3-5 bullets in your own words (a good home is the bottom of `reports/embedding_comparison.md`):

- One surprising nearest-neighbor result - a query that returned something unexpectedly relevant or irrelevant - and what it reveals about how your embedding model understands your domain.
- Would a different embedding model fix it, or is it a chunking problem? Argue from what you observed, not from the lecture.
- One difference you saw between Chroma and Pinecone results - or that you saw none, and why that is the expected outcome.
