# Stage 6 - RAG Eval and Iteration

**Lab:** RAG End-to-End Pipeline (M4 rolling lab)
**Stage:** 6 of 6 - assigned after Lesson 6 (RAG Eval and Iteration)
**Format:** Homework - worked top to bottom.
**Pattern:** B rolling lab stage

> **This is homework.** The Lesson 6 meeting was lecture and a live demo; here you build this stage yourself, on your own capstone. Work top to bottom - later parts build on earlier ones, and every stage builds on the one before it. Commit as you go: M5 assumes this pipeline is complete and committed - it becomes a tool your agents invoke.

## Context

Your RAG pipeline is complete: documents go in, cited answers come out. But does it work well? Without measurement, you're guessing - and with AI systems, your intuition about quality is unreliable. A pipeline that produces great answers for 5 test queries might hallucinate on the 6th. This stage builds the evaluation harness that turns hope into evidence: retrieval metrics, generation faithfulness scoring, citation accuracy checking, a controlled iteration experiment, and a regression baseline that catches future quality degradation.

## Prerequisites

- Complete RAG pipeline from Stages 1-5 (ingest → chunk → embed → retrieve → generate)
- Labeled query set (`tests/eval/labeled_queries.json`) from Stage 4 with at least 10 queries and relevant chunk IDs
- Anthropic API key configured in `.env`
- Full pipeline runnable end-to-end for any query

## Steps

### Part A - Evaluation Harness

### Step 1: Expand the labeled query set

Open `tests/eval/labeled_queries.json` and expand it to at least 15 queries. For each query, add an `expected_answer_summary` - not the exact text you expect, but the semantic intent of a correct answer:

```json
[
  {
    "query": "What is the refund policy for enterprise customers?",
    "relevant_chunk_ids": ["contracts.pdf:chunk_12", "policies.md:chunk_3"],
    "expected_answer_summary": "Enterprise customers can request refunds within 30 days of purchase with manager approval. Partial refunds are prorated.",
    "notes": "Both chunks discuss enterprise refund terms"
  }
]
```

Include a mix of:
- Questions the pipeline should answer well (positive cases)
- Questions the documents partially cover (boundary cases)
- Questions the documents don't cover (negative cases - expect "I don't know")

### Step 2: Build retrieval metrics

Create `src/capstone_ai/rag/evaluator.py` with retrieval measurement functions:

```python
import json
from pathlib import Path

class RAGEvaluator:
    def __init__(self, labeled_queries_path: str = "tests/eval/labeled_queries.json"):
        self.queries = json.loads(Path(labeled_queries_path).read_text())

    def measure_retrieval(self, retriever, k: int = 5) -> dict:
        results = []
        for q in self.queries:
            if not q.get("relevant_chunk_ids"):
                continue
            retrieved = retriever.retrieve(q["query"], top_k=k)
            retrieved_ids = [self._chunk_id(r) for r in retrieved]
            relevant_ids = q["relevant_chunk_ids"]
            precision = self._precision_at_k(retrieved_ids, relevant_ids, k)
            recall = self._recall_at_k(retrieved_ids, relevant_ids, k)
            mrr = self._reciprocal_rank(retrieved_ids, relevant_ids)
            results.append({
                "query": q["query"],
                "precision": precision,
                "recall": recall,
                "mrr": mrr,
            })
        avg = lambda key: sum(r[key] for r in results) / len(results) if results else 0
        return {
            "per_query": results,
            "avg_precision": avg("precision"),
            "avg_recall": avg("recall"),
            "avg_mrr": avg("mrr"),
            "num_queries": len(results),
        }

    def _chunk_id(self, chunk: dict) -> str:
        # Must produce EXACTLY the ID format used in labeled_queries.json
        # ("contracts.pdf:chunk_12"). Both sides derive from source + chunk_index;
        # if they ever disagree, every metric silently reads zero.
        meta = chunk["metadata"]
        return f"{meta.get('source', 'unknown')}:chunk_{meta.get('chunk_index', '?')}"

    def _precision_at_k(self, retrieved: list, relevant: list, k: int) -> float:
        retrieved_at_k = retrieved[:k]
        hits = [r for r in retrieved_at_k if r in relevant]
        return len(hits) / k if k > 0 else 0.0

    def _recall_at_k(self, retrieved: list, relevant: list, k: int) -> float:
        retrieved_at_k = retrieved[:k]
        hits = [r for r in retrieved_at_k if r in relevant]
        return len(hits) / len(relevant) if relevant else 0.0

    def _reciprocal_rank(self, retrieved: list, relevant: list) -> float:
        for i, rid in enumerate(retrieved):
            if rid in relevant:
                return 1.0 / (i + 1)
        return 0.0
```

### Step 3: Build the LLM-as-judge faithfulness scorer

Add a faithfulness scorer that uses Claude to determine whether each claim in a generated answer is supported by the retrieved context:

```python
import anthropic

class FaithfulnessJudge:
    def __init__(self, model: str = "claude-sonnet-5"):
        self.client = anthropic.Anthropic()
        self.model = model

    def score(self, query: str, answer: str, context_chunks: list[dict]) -> dict:
        context_text = "\n\n".join(
            f"[Chunk {i+1}]: {c['text']}" for i, c in enumerate(context_chunks)
        )
        prompt = f"""You are assessing whether a generated answer is faithful to the provided context.

## Context chunks
{context_text}

## Question
{query}

## Generated answer
{answer}

## Task
1. List each factual claim in the generated answer.
2. For each claim, determine if it is SUPPORTED (found in the context), NOT SUPPORTED (not found or contradicted), or PARTIAL (partially supported).
3. If the answer says "I don't know" or similar, and the context truly doesn't cover the question, mark this as CORRECT ABSTENTION.

Respond in this JSON format:
{{
  "claims": [
    {{"claim": "...", "verdict": "SUPPORTED|NOT_SUPPORTED|PARTIAL", "evidence_chunk": 1}}
  ],
  "abstention": true/false,
  "abstention_correct": true/false,
  "faithfulness_score": 0.0-1.0,
  "reasoning": "one sentence summary"
}}"""

        # 4096, not 1024: the model thinks before answering and the claim-level
        # JSON is long - a reply truncated at max_tokens parses as garbage.
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        # Sonnet 5 thinks adaptively, so content[0] is often a ThinkingBlock and
        # content[0].text raises AttributeError. Select the text block by type.
        text = next((b.text for b in response.content if b.type == "text"), "")
        return self._parse_judge_response(text)

    def _parse_judge_response(self, text: str) -> dict:
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            return json.loads(text[start:end])
        except (ValueError, json.JSONDecodeError):
            return {"faithfulness_score": 0.0, "reasoning": "Failed to parse judge response", "raw": text}
```

Wire the judge into the evaluator - add one line to `RAGEvaluator.__init__` so `run_full_assessment` (Step 5) can reach it:

```python
        self.faithfulness_judge = FaithfulnessJudge()
```

### Step 4: Add citation accuracy checking

Add a function that verifies citations in the generated answer actually map to provided chunks:

```python
import re

def check_citation_accuracy(answer: str, context_chunks: list[dict]) -> dict:
    cited = set(int(m) for m in re.findall(r'\[(\d+)\]', answer))
    valid_range = set(range(1, len(context_chunks) + 1))
    valid_citations = cited & valid_range
    fabricated_citations = cited - valid_range
    return {
        "total_citations": len(cited),
        "valid_citations": len(valid_citations),
        "fabricated_citations": sorted(fabricated_citations),
        "citation_accuracy": len(valid_citations) / len(cited) if cited else 1.0,
    }
```

### Step 5: Run the full assessment

Wire everything together and run the complete assessment across all labeled queries:

```python
def run_full_assessment(self, retriever, reranker, generator, k: int = 5) -> dict:
    retrieval_metrics = self.measure_retrieval(retriever, k)
    generation_results = []
    for q in self.queries:
        retrieved = retriever.retrieve(q["query"], top_k=k * 2)
        reranked = reranker.rerank(q["query"], retrieved, top_k=k)
        response = generator.generate(q["query"], reranked)
        faithfulness = self.faithfulness_judge.score(
            q["query"], response["answer"], reranked
        )
        citations = check_citation_accuracy(response["answer"], reranked)
        generation_results.append({
            "query": q["query"],
            "faithfulness_score": faithfulness.get("faithfulness_score", 0),
            "citation_accuracy": citations["citation_accuracy"],
            "fabricated_citations": citations["fabricated_citations"],
        })
    avg = lambda key: sum(r[key] for r in generation_results) / len(generation_results) if generation_results else 0
    return {
        "retrieval": retrieval_metrics,
        "generation": {
            "per_query": generation_results,
            "avg_faithfulness": avg("faithfulness_score"),
            "avg_citation_accuracy": avg("citation_accuracy"),
        },
    }
```

Run the assessment and print the results:

```bash
uv run python -c "
from capstone_ai.rag.evaluator import RAGEvaluator
# ... load pipeline ...
evaluator = RAGEvaluator()
results = evaluator.run_full_assessment(retriever, reranker, generator)
print(f'Retrieval - P@5: {results[\"retrieval\"][\"avg_precision\"]:.2f}, R@5: {results[\"retrieval\"][\"avg_recall\"]:.2f}, MRR: {results[\"retrieval\"][\"avg_mrr\"]:.2f}')
print(f'Generation - Faithfulness: {results[\"generation\"][\"avg_faithfulness\"]:.2f}, Citation accuracy: {results[\"generation\"][\"avg_citation_accuracy\"]:.2f}')
"
```

Spot-check at least 2 queries manually: read the judge's claim-by-claim analysis and verify it makes sense. LLM-as-judge is a heuristic, not ground truth.

**Explain It Back:** Explain what the faithfulness judge's prompt does - how does the judge determine if a claim is supported? What are two ways this judge could give a wrong verdict?

### Part B - Iteration Experiment

### Step 6: Save the baseline

Save current assessment results as the regression baseline:

```python
import json
from datetime import datetime

baseline = {
    "timestamp": datetime.now().isoformat(),
    "config": {
        "chunk_size": 500,  # your current setting
        "chunk_overlap": 100,
        "embedding_model": "all-MiniLM-L6-v2",
        "retrieval_strategy": "hybrid+rerank",
        "top_k": 5,
        "generation_model": "claude-sonnet-5",
    },
    "metrics": results,  # from Step 5
}
with open("tests/eval/baseline.json", "w") as f:
    json.dump(baseline, f, indent=2)
```

### Step 7: Choose one parameter to change

Pick exactly one parameter to modify. Common choices and expected effects:

| Parameter | Change | Likely impact |
|---|---|---|
| Chunk size | 500 → 1000 tokens | Better context per chunk, worse precision (fewer chunks in top-k) |
| Top-k | 5 → 10 | Better recall, possibly worse precision, higher token cost |
| Embedding model | MiniLM → mpnet | Better semantic quality, slower embedding |
| System prompt | Add stronger grounding instruction | Better faithfulness, possibly more "I don't know" |
| Reranking | Remove reranker | Faster, likely worse precision |

Choose based on where your baseline metrics are weakest. If recall is low, try increasing top-k. If faithfulness is low, tighten the prompt. Change ONE thing.

### Step 8: Re-run the assessment

Apply your change, re-run `run_full_assessment`, and compare:

```python
import json
from pathlib import Path

new_results = evaluator.run_full_assessment(modified_retriever, reranker, generator)

baseline = json.loads(Path("tests/eval/baseline.json").read_text())
old_r, old_g = baseline["metrics"]["retrieval"], baseline["metrics"]["generation"]
new_r, new_g = new_results["retrieval"], new_results["generation"]

print("=== Before vs After ===")
print(f"P@5:          {old_r['avg_precision']:.2f} -> {new_r['avg_precision']:.2f}")
print(f"R@5:          {old_r['avg_recall']:.2f} -> {new_r['avg_recall']:.2f}")
print(f"MRR:          {old_r['avg_mrr']:.2f} -> {new_r['avg_mrr']:.2f}")
print(f"Faithfulness: {old_g['avg_faithfulness']:.2f} -> {new_g['avg_faithfulness']:.2f}")
print(f"Citation acc: {old_g['avg_citation_accuracy']:.2f} -> {new_g['avg_citation_accuracy']:.2f}")
```

### Step 9: Write the iteration report

Create `tests/eval/iteration_report.md`:

```markdown
# Iteration Experiment Report

## What I Changed
[Parameter name]: [old value] → [new value]

## Hypothesis
I expected this change to [improve/degrade] [metric] because [reasoning].

## Results

| Metric | Before | After | Delta |
|---|---|---|---|
| Precision@5 | ... | ... | ... |
| Recall@5 | ... | ... | ... |
| MRR | ... | ... | ... |
| Faithfulness | ... | ... | ... |
| Citation accuracy | ... | ... | ... |

## Analysis
[Which metrics improved? Which degraded? Was the hypothesis correct?]

## Decision
[SHIP / REVERT] - [one sentence justification]

## What I'd Try Next
[If you had another iteration cycle, what parameter would you change and why?]
```

There is deliberately no "right answer" here. Your metrics will likely improve in some areas and degrade in others. You must reason about the tradeoff for your specific use case and defend your decision.

### Step 10: Commit

```bash
git add src/capstone_ai/rag/evaluator.py tests/eval/baseline.json tests/eval/iteration_report.md tests/eval/labeled_queries.json
git commit -m "stage-6: assessment harness with faithfulness scoring, iteration experiment, regression baseline"
```

## Success Criteria - You're Done When...

- [ ] Labeled query set has at least 15 queries with relevant chunks AND expected answer summaries
- [ ] Retrieval metrics (precision@5, recall@5, MRR) are computed and reported
- [ ] LLM-as-judge faithfulness scorer grades each query's generated answer
- [ ] Citation accuracy checker validates that cited chunk numbers are real
- [ ] Baseline metrics are saved to `tests/eval/baseline.json`
- [ ] One iteration experiment is complete with a before/after comparison
- [ ] Iteration report is written with hypothesis, results, and a ship/revert decision
- [ ] Full assessment can be re-run with a single command

## Quality Checklist (Best Practices Ownership)

- [ ] Labeled test set has at least 15 queries with human-judged relevant chunks AND expected answer summaries
- [ ] Retrieval metrics are computed correctly - spot-check at least one query manually (count relevant hits yourself and verify the computed precision)
- [ ] Faithfulness scorer uses a detailed judge prompt (claim-level analysis, not just "is this faithful? yes/no")
- [ ] Citation accuracy is checked programmatically, not by reading outputs
- [ ] Baseline metrics are saved to a file (not just printed to console)
- [ ] Iteration experiment changes exactly ONE parameter (controlled experiment)
- [ ] Iteration report includes hypothesis, metrics table, analysis, and decision with reasoning
- [ ] Full assessment is runnable with a single script or command, not a manual multi-step process

## Explain It Back

After your assessment harness is working, explain in writing (3-5 sentences):

1. How does the faithfulness judge determine if a claim is supported by the context? What are two failure modes of this approach?
2. Your iteration experiment changed one parameter and some metrics improved while others degraded. How did you decide whether to ship or revert? What would change that decision?
3. Why is it important to save baseline metrics to a file rather than just comparing printouts? When would the baseline need to be regenerated?

## Stretch Goals

- Add a relevance scorer: does the answer actually address the question, or does it answer a related but different question? Implement as a separate LLM-as-judge assessment.
- Build a CI-compatible runner: a script that loads the baseline, runs the assessment, compares, and exits non-zero if any metric drops below a configurable threshold.
- Compare faithfulness scores between Claude Sonnet and Claude Haiku as the generation model. Does the cheaper model hallucinate more? By how much?

## Common Pitfalls and Recovery

| Pitfall | How to recognize it | How to recover |
|---|---|---|
| Labeled queries have wrong relevance labels | Metrics look surprisingly bad or surprisingly good | Spot-check 5 queries manually. If your labels are wrong, your metrics are meaningless. Fix the labels first. |
| Faithfulness judge returns unparseable JSON | `_parse_judge_response` hits the fallback branch | Add "Respond with ONLY the JSON object, no additional text" to the judge prompt. Also check `response.stop_reason` - a reply truncated at `max_tokens` parses as garbage; raise the limit or retry the call once. |
| All faithfulness scores are 1.0 | Judge says everything is supported | The judge prompt may be too lenient. Add examples of NOT_SUPPORTED claims. Or your pipeline genuinely doesn't hallucinate - verify manually. |
| Iteration results are identical to baseline | Delta is 0.00 on all metrics | The parameter change may be too small to measure on 15 queries. Try a larger change, or expand the test set. |
| API costs from judge calls | Running the assessment is expensive (one Claude call per query for judging) | Use Claude Haiku for the judge model to reduce cost. Cache judge results for unchanged query/answer pairs. |

## Capstone Connection

Now apply this to your capstone:
- The assessment harness is a permanent fixture - every time you change the pipeline, re-run the assessment
- The regression baseline catches silent quality degradation when you update documents, change models, or modify prompts
- Carry this practice into M5 (Agentic AI) and M6 (Security & Cost) - the patterns generalize beyond RAG

After this stage, your capstone has: an assessment harness that quantifies retrieval and generation quality, a completed iteration experiment with a data-driven decision, and a regression baseline for ongoing quality monitoring. This fulfills the module-level capstone goal: "a deployed RAG pipeline over real documents, with a harness measuring retrieval quality and answer faithfulness."

## Connection to Next Module

M4 is complete. You've built a RAG pipeline from architecture through measurement. In M5 (Agentic AI), this pipeline becomes a tool that agents decide when and how to invoke - your retriever and generator become callable tools in an agent loop. In M6, the assessment practices you started here deepen into production-grade testing, security auditing, and cost engineering. The discipline of "change one thing, measure, decide" carries forward to every AI system you build.

## What I Learned

Write 3-6 bullets in your own words (a good home is the bottom of `tests/eval/iteration_report.md`):

- Your iteration experiment in three sentences: what you changed, what your hypothesis was, what the metrics showed - and whether you'd ship it.
- Would your decision change if this system served medical queries instead of your domain? What does that say about metric thresholds?
- What would you try next if you had another iteration cycle?
- One place your intuition about quality was wrong before you measured. (Look back at the failure modes you guessed in Stage 1's architecture doc - did the harness confirm them?)
