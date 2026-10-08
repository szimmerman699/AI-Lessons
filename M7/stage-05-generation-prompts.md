# Stage 5 - Generation Prompts

**Lab:** RAG End-to-End Pipeline (M4 rolling lab)
**Stage:** 5 of 6 - assigned after Lesson 5 (Generation Prompts)
**Format:** Homework - worked top to bottom.
**Pattern:** B rolling lab stage

> **This is homework.** The Lesson 5 meeting was lecture and a live demo; here you build this stage yourself, on your own capstone. Work top to bottom - later parts build on earlier ones, and every stage builds on the one before it. Commit as you go: Stage 6 assumes everything here is committed and working.

## Context

Your retrieval pipeline returns relevant, well-ranked chunks. Now you turn them into trustworthy answers. This is where many RAG systems fail silently: the retrieval is perfect, but the LLM ignores the context, fabricates citations, or confidently answers questions the documents don't cover. You build a generation layer that grounds responses in retrieved context, cites its sources, and knows when to say "I don't know." You also add streaming for responsive user experience.

## Prerequisites

- Working hybrid retrieval pipeline with reranking from Stage 4
- Labeled query set (`tests/eval/labeled_queries.json`) with at least 10 queries
- Anthropic API key configured in `.env`
- `anthropic` SDK in the project (from M3, re-confirmed in Stage 1)

## Steps

### Part A - Generation Layer

### Step 1: Design the system prompt

Create `src/capstone_ai/prompts/system_prompt.md` - a versioned file (not a hardcoded string) containing your generation system prompt. Start with this structure and adapt for your capstone's domain:

```markdown
You are a knowledgeable assistant that answers questions based on provided context documents.

## Rules
- Answer ONLY based on the provided context. Do not use information from your training data.
- For each claim in your answer, cite the source using [1], [2], etc., corresponding to the numbered context chunks.
- If the provided context does not contain enough information to answer the question, say: "I don't have enough information in the available documents to answer this question."
- If the context partially answers the question, provide what you can and explicitly state what information is missing.
- If context chunks contain contradictory information, acknowledge the contradiction and cite both sources.
- Keep answers concise and focused on the question asked.
```

Store this as a file because prompts are code - they deserve version control and review.

### Step 2: Build the Generator class

Create `src/capstone_ai/rag/generator.py`:

```python
import anthropic
from pathlib import Path

class Generator:
    def __init__(
        self,
        model: str = "claude-sonnet-5",
        max_context_tokens: int = 4000,
        prompt_path: str = "src/capstone_ai/prompts/system_prompt.md",
    ):
        self.client = anthropic.Anthropic()
        self.model = model
        self.max_context_tokens = max_context_tokens
        self.system_prompt = Path(prompt_path).read_text()

    def generate(self, query: str, retrieved_chunks: list[dict]) -> dict:
        included, context_block = self._build_context(retrieved_chunks)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=self.system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"## Context\n{context_block}\n\n## Question\n{query}",
                }
            ],
        )
        # Sonnet 5 thinks adaptively, so content[0] is often a ThinkingBlock and
        # content[0].text raises AttributeError. Select the text block by type.
        answer = next((b.text for b in response.content if b.type == "text"), "")
        return {
            "answer": answer,
            "chunks_included": len(included),
            "chunks_dropped": len(retrieved_chunks) - len(included),
            "model": self.model,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        }

    def _build_context(self, chunks: list[dict]) -> tuple[list[dict], str]:
        # Select chunks that fit within the token budget, and return WHICH
        # chunks made it in - the citation map in Step 4 needs exactly that list.
        # Rough estimate: 1 token ≈ 4 characters
        included = []
        context_parts = []
        total_chars = 0
        char_budget = self.max_context_tokens * 4
        for i, chunk in enumerate(chunks):
            chunk_text = f"[{i + 1}] (Source: {chunk['metadata'].get('source', 'unknown')})\n{chunk['text']}"
            if total_chars + len(chunk_text) > char_budget:
                break
            included.append(chunk)
            context_parts.append(chunk_text)
            total_chars += len(chunk_text)
        return included, "\n\n".join(context_parts)
```

### Step 3: Test generation on your labeled queries

Run 5 queries from your labeled set through the full pipeline (retrieve → rerank → generate). For each, inspect:

- Does the answer use information only from the retrieved chunks?
- Are citations present and do they map to the correct chunk numbers?
- Does the answer address the question directly?

```bash
uv run python -c "
from capstone_ai.rag.retriever import HybridRetriever, Reranker
from capstone_ai.rag.generator import Generator
# ... load pipeline ...
query = 'your test query here'
results = hybrid.retrieve(query)
reranked = reranker.rerank(query, results, top_k=5)
response = generator.generate(query, reranked)
print(response['answer'])
"
```

### Step 4: Add citation tracking

Extend `Generator` to return a mapping of citation numbers to source chunks:

```python
def generate_with_citations(self, query: str, retrieved_chunks: list[dict]) -> dict:
    result = self.generate(query, retrieved_chunks)
    # Map citations to the chunks that actually made it into the context - the
    # token budget may have dropped the tail of the retrieved list, and a [3]
    # that points at a chunk the model never saw is worse than no map at all.
    included, _ = self._build_context(retrieved_chunks)
    citation_map = {}
    for i, chunk in enumerate(included):
        citation_map[f"[{i + 1}]"] = {
            "source": chunk["metadata"].get("source", "unknown"),
            "text_preview": chunk["text"][:200],
        }
    result["citation_map"] = citation_map
    return result
```

Verify that citations in the generated answer actually correspond to the chunks passed in. If the model cites `[3]` but only 2 chunks were provided, that's a fabricated citation - your prompt needs tightening.

**Explain It Back:** After Claude helps you design and iterate on the system prompt, identify the specific instruction that handles hallucination prevention. Explain why it works and describe a scenario where it might still fail.

### Part B - Hardening

### Step 5: Implement "I don't know" handling

Test with queries your documents cannot answer:

```python
out_of_scope_queries = [
    "What is the population of Mars?",
    "Explain quantum computing in detail",
    # Add 2-3 queries specific to your domain that are plausible but not covered
]
```

For each, run the full pipeline and verify the model responds with an "I don't know" variant rather than hallucinating. If it still answers confidently, strengthen the system prompt.

### Step 6: Add streaming responses

Add a streaming method using the Anthropic SDK:

```python
def generate_stream(self, query: str, retrieved_chunks: list[dict]):
    _, context_block = self._build_context(retrieved_chunks)
    with self.client.messages.stream(
        model=self.model,
        max_tokens=1024,
        system=self.system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"## Context\n{context_block}\n\n## Question\n{query}",
            }
        ],
    ) as stream:
        full_response = ""
        for text in stream.text_stream:
            print(text, end="", flush=True)
            full_response += text
        print()
    return full_response
```

Run a query with streaming and verify tokens appear incrementally.

### Step 7: Handle edge cases

Test and handle these scenarios:

1. **Empty retrieval** - retriever returns no results. Your generator should produce a graceful message ("I couldn't find relevant information in the available documents") without calling the LLM with empty context.

2. **Conflicting context** - two retrieved chunks say different things. Test with a query where this happens (or craft one). Verify the model acknowledges the contradiction and cites both sources.

3. **Context overflow** - more retrieved chunks than fit in the token budget. Verify `_build_context` correctly truncates and only includes chunks that fit. Log how many chunks were dropped.

```python
def generate(self, query: str, retrieved_chunks: list[dict]) -> dict:
    if not retrieved_chunks:
        return {
            "answer": "I couldn't find relevant information in the available documents to answer this question.",
            "chunks_included": 0,
            "chunks_dropped": 0,
            "model": self.model,
            "usage": {"input_tokens": 0, "output_tokens": 0},
        }
    # ... rest of generation logic
```

### Step 8: Test with misleading context

This is the productive friction moment. Find or craft a query where the retrieved chunks contain similar keywords but answer a different question. For example, if your documents discuss both "Python programming" and "Python snake care," query about one and observe whether chunks about the other contaminate the answer.

Observe the hallucination. Then fix the system prompt - add an instruction that addresses this specific failure mode. Document what you changed and why.

### Step 9: Commit

```bash
git add src/capstone_ai/rag/generator.py src/capstone_ai/prompts/system_prompt.md
git commit -m "stage-5: generation layer with citations, streaming, and edge case handling"
```

## Success Criteria - You're Done When...

- [ ] Generator produces answers grounded in retrieved context with inline citations
- [ ] Citations map to actual source chunks (no fabricated references)
- [ ] System prompt is stored as a versioned file in `src/capstone_ai/prompts/`
- [ ] Token budget is enforced - context block never exceeds `max_context_tokens`
- [ ] "I don't know" response works for out-of-scope queries
- [ ] Streaming output delivers tokens incrementally
- [ ] Empty retrieval, conflicting context, and context overflow are all handled gracefully

## Quality Checklist (Best Practices Ownership)

- [ ] System prompt explicitly instructs the model to answer only from provided context
- [ ] Citations map to specific source chunks - verify by cross-referencing citation numbers with the context block
- [ ] Token budget is enforced programmatically (not assumed to fit)
- [ ] "I don't know" response is tested with at least 3 out-of-scope queries
- [ ] Streaming is implemented using `client.messages.stream()`, not polling
- [ ] Empty retrieval produces a graceful message, not an API error or hallucination
- [ ] Prompt template is stored as a file and loaded at runtime, not hardcoded in a function

## Explain It Back

After your generation layer is working, explain in writing (3-5 sentences):

1. Point to the exact instruction in your system prompt that prevents hallucination. Describe a scenario where it might still fail.
2. Why does chunk ordering matter when building the context block? What happens if you put the least relevant chunk first?
3. Why is streaming important for a RAG application's user experience, beyond "it feels faster?"

## Stretch Goals

- Implement structured JSON output alongside natural language: when called via API, return `{"answer": "...", "citations": [...], "confidence": 0.85}`. Keep the natural language mode for chat UIs.
- Add a confidence estimate based on retrieval similarity scores - if the best retrieved chunk has a low similarity score, flag the answer as low-confidence.
- Compare generation quality between Claude Sonnet and Claude Haiku on the same retrieval results. Measure token cost per query for each.

## Common Pitfalls and Recovery

| Pitfall | How to recognize it | How to recover |
|---|---|---|
| Model ignores context and answers from training data | Answer is correct but doesn't cite sources, or cites non-existent sources | Strengthen the system prompt: "You MUST cite a source for every factual claim. If you cannot cite a source, say you don't know." |
| Fabricated citations | Model cites `[4]` but only 3 chunks were provided | Add post-processing: validate that every citation number maps to an actual chunk. Flag invalid citations in the response. |
| "I don't know" is too aggressive | Model refuses to answer questions the context does cover | Relax the prompt: change from "say I don't know" to "if the context doesn't contain enough information, explain what's missing" |
| Token budget miscalculation | API returns a context-length error | The character-to-token estimate (4 chars ≈ 1 token) is rough. Count precisely with `client.messages.count_tokens(...)` (a free endpoint), or reduce the budget by 20% as safety margin. |
| Streaming drops partial responses | Incomplete output when the stream is interrupted | Wrap the stream in try/except and return whatever was accumulated. Log the interruption. |

## Capstone Connection

Now apply this to your capstone:
- Adapt the system prompt for your capstone's domain and tone (formal for legal docs, conversational for customer support, technical for engineering docs)
- Test generation against your capstone's real queries from the labeled query set
- The citation format should match what your capstone's users expect (academic-style `[1]`, inline source names, or footnotes)

After this stage, your capstone has: a complete RAG pipeline (ingest → chunk → embed → retrieve → generate) that produces cited answers, handles edge cases, and streams responses.

## Connection to Next Stage

Stage 6 measures whether this pipeline actually works well. You'll build an eval harness that quantifies retrieval quality and answer faithfulness, run a controlled experiment to improve one parameter, and establish a regression baseline. The generation layer you just built is what gets evaluated - if your answers are bad, Stage 6 will tell you exactly where the quality breaks down.

## What I Learned

Write 3-5 bullets in your own words (a good home is a homework-notes file next to `src/capstone_ai/prompts/system_prompt.md`):

- Your worst hallucination example - a query where the model answered beyond the context despite your system prompt - and the prompt change that fixed (or reduced) it.
- Is that fix robust, or could a different query bypass it? How?
- How would you detect this failure automatically? (Stage 6 makes this concrete.)
