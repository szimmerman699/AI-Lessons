# Stage 4 - Retrieval and Reranking

**Lab:** RAG End-to-End Pipeline (M4 rolling lab)
**Stage:** 4 of 6 - assigned after Lesson 4 (Retrieval and Reranking)
**Format:** Homework - worked top to bottom.
**Pattern:** B rolling lab stage

> **This is homework.** The Lesson 4 meeting was lecture and a live demo; here you build this stage yourself, on your own capstone. Work top to bottom - later parts build on earlier ones, and every stage builds on the one before it. Commit as you go: Stage 5 assumes everything here is committed and working.

## Context

Your chunks are embedded and indexed in both Chroma and Pinecone. Dense retrieval (vector similarity) finds semantically similar chunks - but similar isn't always relevant. A query about "refund policy for enterprise contracts" might return chunks about consumer refund policies: similar words, wrong context. This stage adds precision: sparse retrieval (BM25) for keyword-exact matches, hybrid search that combines both signals, cross-encoder reranking for fine-grained relevance scoring, and MMR for result diversity. You also build the labeled query set that seeds your eval harness in Stage 6.

## Prerequisites

- Working embedding pipeline from Stage 3 with chunks indexed in Chroma and Pinecone
- `VectorStoreBackend` interface supporting both backends
- At least 20 indexed chunks from your document set
- `rank-bm25` in the project (added in Stage 1) and `sentence-transformers` with the CPU torch pin (added in Stage 3, Step 0)

## Steps

### Part A - Hybrid Retrieval

### Step 1: Add BM25 sparse retrieval

Create or expand `src/capstone_ai/rag/retriever.py` with a `SparseRetriever` class that indexes chunk texts using BM25:

```python
from rank_bm25 import BM25Okapi

class SparseRetriever:
    def __init__(self, chunks: list[dict]):
        self.chunks = chunks
        tokenized = [chunk["text"].lower().split() for chunk in chunks]
        self.bm25 = BM25Okapi(tokenized)

    def retrieve(self, query: str, top_k: int = 10) -> list[dict]:
        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)
        top_indices = scores.argsort()[-top_k:][::-1]
        return [
            {**self.chunks[i], "score": float(scores[i]), "source": "sparse"}
            for i in top_indices if scores[i] > 0
        ]
```

### Step 2: Build a dense retriever wrapper

Add a `DenseRetriever` class that wraps your vector store backend from Stage 3:

```python
class DenseRetriever:
    def __init__(self, vector_store, embedder):
        self.vector_store = vector_store
        self.embedder = embedder

    def retrieve(self, query: str, top_k: int = 10) -> list[dict]:
        query_embedding = self.embedder.embed_text(query)
        results = self.vector_store.query(query_embedding, top_k=top_k)
        for r in results:
            r["source"] = "dense"
        return results
```

You'll need to add an `embed_text` method to your `EmbeddingPipeline` from Stage 3 that embeds a single string (the query).

### Step 3: Implement reciprocal rank fusion (RRF)

Add a `HybridRetriever` class that combines dense and sparse results using RRF:

```python
class HybridRetriever:
    def __init__(self, dense: DenseRetriever, sparse: SparseRetriever, k: int = 60):
        self.dense = dense
        self.sparse = sparse
        self.k = k  # RRF constant - controls how much rank position matters

    def retrieve(self, query: str, top_k: int = 10) -> list[dict]:
        dense_results = self.dense.retrieve(query, top_k=top_k * 2)
        sparse_results = self.sparse.retrieve(query, top_k=top_k * 2)
        return self._fuse(dense_results, sparse_results, top_k)

    def _fuse(self, dense_results, sparse_results, top_k):
        # Metadata fields (e.g. "source") are backend-dependent - not every
        # vector store or chunk schema guarantees their presence.
        scores = {}
        chunk_map = {}
        for rank, result in enumerate(dense_results):
            source = result.get("metadata", {}).get("source", "unknown")
            chunk_id = source + ":" + result["text"][:50]
            scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (self.k + rank + 1)
            chunk_map[chunk_id] = result
        for rank, result in enumerate(sparse_results):
            source = result.get("metadata", {}).get("source", "unknown")
            chunk_id = source + ":" + result["text"][:50]
            scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (self.k + rank + 1)
            chunk_map[chunk_id] = result
        sorted_ids = sorted(scores, key=scores.get, reverse=True)[:top_k]
        return [
            {**chunk_map[cid], "rrf_score": scores[cid], "source": "hybrid"}
            for cid in sorted_ids
        ]
```

### Step 4: Compare retrieval strategies on test queries

Create 5 test queries that exercise different retrieval needs:

1. A semantic query (meaning-based, no exact keywords in the documents)
2. A keyword-specific query (exact term that BM25 should catch)
3. A query that both strategies should handle well
4. A query with domain jargon that might confuse dense retrieval
5. A query about a topic not covered in your documents (negative test)

Run all three strategies (dense-only, sparse-only, hybrid) on each query. Save results to `reports/retrieval_comparison.md` with a table showing the top-5 results per strategy per query.

```bash
uv run python -c "
from capstone_ai.rag.retriever import DenseRetriever, SparseRetriever, HybridRetriever
# ... load your pipeline components ...
# Run each query through all three strategies and print results
"
```

**Explain It Back:** Before proceeding, explain in your own words: Why does RRF use rank position (1/(k + rank)) rather than raw similarity scores? What problem does the constant `k` solve?

Instead of comparing two search methods' confusing "scores," we just look at where each one ranks a result in its list and give extra credit when both put it near the top, and the constant `k` keeps one method's #1 pick from overpowering everything else.
### Part B - Reranking + Evaluation

### Step 5: Add cross-encoder reranking

Add a `Reranker` class that re-scores retrieved results using a cross-encoder:

```python
from sentence_transformers import CrossEncoder

class Reranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, results: list[dict], top_k: int = 5) -> list[dict]:
        if not results:
            return []
        pairs = [(query, r["text"]) for r in results]
        scores = self.model.predict(pairs)
        for result, score in zip(results, scores):
            result["rerank_score"] = float(score)
        reranked = sorted(results, key=lambda r: r["rerank_score"], reverse=True)
        return reranked[:top_k]
```

Integrate this into your pipeline: retrieve broadly (top-20 from hybrid), then rerank to final top-5.

### Step 6: Implement Maximal Marginal Relevance (MMR)

Add an MMR function that selects diverse results:

```python
import numpy as np

def _cosine_sim(a: list[float], b: list[float]) -> float:
    a, b = np.asarray(a), np.asarray(b)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))

def mmr_select(
    results: list[dict],
    top_k: int = 5,
    lambda_param: float = 0.7,
) -> list[dict]:
    if len(results) <= top_k:
        return results

    # Cross-encoder logits are unbounded and RRF scores are tiny fractions;
    # cosine similarity lives in [0, 1]. Min-max normalise relevance first -
    # subtract two numbers on different scales and lambda_param means nothing.
    raw = [r.get("rerank_score", r.get("rrf_score", 0.0)) for r in results]
    spread = max(raw) - min(raw)
    for r, score in zip(results, raw):
        r["_relevance"] = (score - min(raw)) / spread if spread else 1.0

    selected = [results[0]]
    remaining = list(results[1:])
    while len(selected) < top_k and remaining:
        best_score = -float("inf")
        best_idx = 0
        for i, candidate in enumerate(remaining):
            max_sim = max(
                _cosine_sim(candidate["embedding"], s["embedding"])
                for s in selected
            )
            mmr = lambda_param * candidate["_relevance"] - (1 - lambda_param) * max_sim
            if mmr > best_score:
                best_score = mmr
                best_idx = i
        selected.append(remaining.pop(best_idx))
    return selected
```

The `lambda_param` controls the relevance-vs-diversity tradeoff. Higher values favor relevance; lower values favor diversity. Make this configurable.

MMR compares result embeddings, so every result dict must carry its `embedding`. Sparse results have it from Stage 3's `embed_chunks`; for dense results, make sure your `VectorStoreBackend.query` returns embeddings too (in Chroma, add `"embeddings"` to the query's `include` list).

### Step 7: Build a labeled query set

Create `tests/eval/labeled_queries.json` with 10-15 queries. For each query, manually identify which chunks are relevant:

```json
[
  {
    "query": "What is the refund policy for enterprise customers?",
    "relevant_chunk_ids": ["contracts.pdf:chunk_12", "policies.md:chunk_3"],
    "notes": "Both chunks discuss enterprise refund terms"
  }
]
```

This requires reading your chunks and making relevance judgments. Do not ask Claude to generate the labels - your labels are your definition of quality. If they're wrong, every metric you build on them lies.

Use `source:chunk_{chunk_index}` as the ID convention - both fields are already in every chunk's metadata (Stage 2, Step 9). Stage 6's evaluator derives IDs from retrieved chunks the same way, and the two must produce identical strings: if labels and retrieval disagree on the ID format, every metric silently reads zero.

### Step 8: Compute retrieval metrics

Add metric computation to your pipeline:

```python
def precision_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int) -> float:
    retrieved_at_k = retrieved_ids[:k]
    relevant_retrieved = [rid for rid in retrieved_at_k if rid in relevant_ids]
    return len(relevant_retrieved) / k if k > 0 else 0.0

def recall_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int) -> float:
    retrieved_at_k = retrieved_ids[:k]
    relevant_retrieved = [rid for rid in retrieved_at_k if rid in relevant_ids]
    return len(relevant_retrieved) / len(relevant_ids) if relevant_ids else 0.0
```

Run all strategies (dense, sparse, hybrid, hybrid+rerank) against the labeled query set. Compute precision@5 and recall@5 for each. Add the comparison to `reports/retrieval_comparison.md`.

### Step 9: Commit

```bash
git add src/capstone_ai/rag/retriever.py tests/eval/labeled_queries.json reports/retrieval_comparison.md
git commit -m "stage-4: hybrid retrieval, reranking, and labeled query set"
```

## Success Criteria - You're Done When...

- [ ] Dense, sparse, and hybrid retrieval all return results for your test queries
- [ ] RRF fusion combines dense and sparse results into a single ranked list
- [ ] Cross-encoder reranker re-scores the hybrid top-20 into a final top-5
- [ ] MMR diversity selection is implemented and configurable via `lambda_param`
- [ ] Labeled query set has at least 10 queries with manually tagged relevant chunk IDs
- [ ] Precision@5 and recall@5 are computed for each retrieval strategy
- [ ] `reports/retrieval_comparison.md` shows a side-by-side comparison

## Quality Checklist (Best Practices Ownership)

- [ ] Hybrid retrieval combines dense and sparse results (not just one or the other)
- [ ] Reciprocal rank fusion uses rank positions, not raw scores - the `k` parameter is justified
- [ ] Reranker is applied after initial retrieval (two-stage architecture), not replacing it
- [ ] MMR diversity parameter (`lambda_param`) is configurable, not hardcoded
- [ ] Labeled query set includes at least 10 queries with human-judged relevant chunks
- [ ] Evaluation metrics are computed programmatically (not eyeballed from printouts)
- [ ] Retrieval parameters (top-k, similarity threshold, RRF constant) are all configurable

## Explain It Back

After your retrieval pipeline is working, explain in writing (3-5 sentences):

1. Why two-stage retrieval (retrieve broadly, rerank precisely) outperforms single-stage retrieval - what does each stage contribute?
2. When would hybrid search outperform dense-only retrieval? Give a concrete example from your document set.
3. What tradeoff does the MMR `lambda_param` control, and what value would you choose for your capstone's use case?

## Stretch Goals

- Implement HyDE (Hypothetical Document Embeddings): generate a hypothetical answer to the query, embed it, and use that embedding for retrieval. Compare quality against standard dense retrieval.
- Add per-query latency measurement. How much time does reranking add? At what result set size does it become too slow for interactive use?
- Implement a simple A/B test framework: run the same queries through two configurations and output a statistical comparison of metric differences.

## Common Pitfalls and Recovery

| Pitfall | How to recognize it | How to recover |
|---|---|---|
| BM25 returns no results | All scores are 0 for every query | Check tokenization - BM25 needs word-level tokens. If your chunks contain special characters or unusual formatting, preprocess them. |
| RRF scores are all identical | Every fused result has the same score | Verify that both dense and sparse results are being incorporated. If one retriever returns nothing, RRF degenerates to single-source ranking. |
| Reranker is slow | Cross-encoder takes >5 seconds for top-20 | This is normal for CPU inference. Reduce the candidate set (top-10 instead of top-20) or use a smaller cross-encoder model. |
| Labeled query set has ambiguous relevance | You can't decide if a chunk is relevant or not | Write more specific queries, or split the ambiguous label into "definitely relevant" vs "partially relevant." For metrics, count only "definitely relevant." |
| MMR selects irrelevant diverse results | Results are diverse but some are off-topic | Increase `lambda_param` toward 1.0 to weight relevance more heavily. MMR at lambda=1.0 is pure relevance (no diversity). |

## Capstone Connection

Now apply this to your capstone:
- Build the labeled query set from real questions your capstone's users would ask
- Choose the retrieval strategy (dense, hybrid, hybrid+rerank) that performs best on your labeled queries
- The labeled query set carries forward to Stage 6 - expand it there with expected answers for generation evaluation

After this stage, your capstone has: a retrieval layer that returns relevant, well-ranked results using hybrid search with reranking, and a labeled query set with measured precision and recall.

## Connection to Next Stage

Stage 5 takes your retrieved chunks and turns them into trustworthy answers. The generation layer consumes whatever your retriever returns - so retrieval quality directly determines answer quality. Before moving on, verify that your top-5 results for each labeled query are actually relevant. Bad retrieval cannot be fixed by better prompts.

## What I Learned

Write 3-5 bullets in your own words (a good home is the bottom of `reports/retrieval_comparison.md`):

- One query where your retrieval pipeline surprised you - a result you didn't expect to rank highly, or a relevant chunk that was missed.
- What would you change to fix it - the retrieval strategy, the embeddings, or the chunks? Why that layer?
- How confident are you in your relevance labels, and what would make you more confident?
