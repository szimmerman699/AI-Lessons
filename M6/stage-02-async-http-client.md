# Stage 2 - Async HTTP Client Layer

**Lesson:** 2 of 5 (Async and Httpx)
**Prerequisites:** Stage 1 complete - working project with `pyproject.toml`, dependencies installed via `uv sync` (uv manages `.venv` for you - you never activate it), `.env` with API key

## Context

Every LLM API call takes 1-30 seconds. If your code waits for each one sequentially, 10 calls cost 10-300 seconds of wall time. With async concurrency, the same 10 calls run in ~1-30 seconds total. Async isn't a nice-to-have in AI engineering - it's how applications survive real-world latency.

In this stage, you build the async HTTP client layer that will underpin all Anthropic SDK calls (Stage 3), your FastAPI server (Stage 4), and your test harness (Stage 5).

---

## Steps

### Step 1 - Sync Baseline: Measure the Problem

Create `src/capstone_ai/core/http_client.py`. Start with a synchronous implementation to establish the baseline:

```python
import time
import httpx


def fetch_sync(url: str, count: int = 5) -> list[dict]:
    results = []
    with httpx.Client(timeout=10.0) as client:
        for i in range(count):
            start = time.perf_counter()
            response = client.get(url)
            elapsed = time.perf_counter() - start
            results.append({"status": response.status_code, "elapsed": round(elapsed, 3)})
    return results


if __name__ == "__main__":
    url = "https://httpbingo.org/delay/1"
    start = time.perf_counter()
    results = fetch_sync(url, count=5)
    total = time.perf_counter() - start
    print(f"Sync: {len(results)} requests in {total:.2f}s")
    for r in results:
        print(f"  {r['status']} in {r['elapsed']}s")
```

Run it:

```bash
uv run python -m capstone_ai.core.http_client
```

Expected: **~6-7 seconds** total (5 sequential requests; `/delay/1` is 1 second of server-side delay *plus* the network round-trip, so each one costs ~1.2-1.3s in practice). Record your own number - it's your baseline, and the ratio is what matters, not the absolute.


My number: Sync: 5 requests in 6.56s

If you see `ConnectError` or `TimeoutException`, check your internet connection. `httpbingo.org` is a free public service - if it is down or rate-limiting you, swap in one of these drop-in replacements (identical `/delay/N`, `/status/N`, `/get` routes):

- `https://postman-echo.com`
- a local server you run yourself:
  ```bash
  uv run --with httpbin --with gunicorn gunicorn -b 127.0.0.1:8000 --threads 32 httpbin:app
  ```
  Leave it running in a spare terminal and use `http://127.0.0.1:8000` as your base URL. Keep the `--threads 32` - without it the server handles one request at a time and your async version will look exactly as slow as the sync one.

### Step 2 - Convert to Async

Add the async version to the same file - **insert it above the `if __name__ == "__main__":` block, not at the end of the file.** Python executes top to bottom: anything below `__main__` is defined after that block has already run, so appending gives you `NameError: name 'asyncio' is not defined`.

```python
import asyncio


async def fetch_async(url: str, count: int = 5) -> list[dict]:
    results = []
    async with httpx.AsyncClient(timeout=10.0) as client:
        async def _fetch_one() -> dict:
            start = time.perf_counter()
            response = await client.get(url)
            elapsed = time.perf_counter() - start
            return {"status": response.status_code, "elapsed": round(elapsed, 3)}

        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(_fetch_one()) for _ in range(count)]
        results = [t.result() for t in tasks]
    return results
```

Update the `__main__` block to run both:

```python
if __name__ == "__main__":
    url = "https://httpbingo.org/delay/1"

    # Sync
    start = time.perf_counter()
    sync_results = fetch_sync(url, count=5)
    sync_total = time.perf_counter() - start
    print(f"Sync:  {len(sync_results)} requests in {sync_total:.2f}s")

    # Async
    start = time.perf_counter()
    async_results = asyncio.run(fetch_async(url, count=5))
    async_total = time.perf_counter() - start
    print(f"Async: {len(async_results)} requests in {async_total:.2f}s")
    print(f"Speedup: {sync_total / async_total:.1f}x")
```

Run it. Expected: **~1.4-1.6 seconds, a 4-4.5x speedup** against `httpbingo.org`. The speedup comes from overlapping I/O waits.


Why not a clean 5x? The five requests now share one wall-clock second of server delay, but each still pays its own network round-trip, and the async path opens five TLS connections at once instead of reusing one. Against a *local* httpbin the same code lands near 1.05s and ~4.9x, because the round-trip disappears. **Quote the number your terminal prints.** The teaching point is that nothing got faster - the waiting got shared - and that survives whatever ratio you actually measure.

** Sync:  5 requests in 5.10s
Async: 5 requests in 1.03s
Speedup: 5.0x
**

If you see `ExceptionGroup` errors, one of the requests failed inside the `TaskGroup`. Read the error - `TaskGroup` surfaces all failures, not just the first.

### Step 3 - Add Rate Limiting with Semaphore (Optional)

> **Optional.** The `fetch_rate_limited` function you build here gets deleted in Step 5 anyway, and the semaphore is rebuilt into the `AsyncHTTPClient` class there - so the concept still gets practiced either way. Skip the standalone measurement if you're pressed for time; do read the rate-limit discussion below, because it explains *why* the class in Step 5 has a semaphore at all.

AI providers enforce rate limits, and the limit that actually bites is not the one people expect. Anthropic's entry-level tier, for example, allows on the order of **1,000 requests per minute** - you will almost never hit that. What you *will* hit is the token limit: around **2 million input tokens and 400 thousand output tokens per minute** at that tier. Fan out 200 concurrent LLM calls with long prompts and you blow the token budget, not the request budget, and you eat `429 Too Many Requests`.

You cannot control tokens-per-minute directly, but you can control how much work is in flight at once. That is what a semaphore gives you.

Rate limits change - check the Limits page in your own Console for your org's actual tier (see the [rate limit docs](https://platform.claude.com/docs/en/api/rate-limits)).

Add a rate-limited version:

```python
async def fetch_rate_limited(
    url: str,
    count: int = 10,
    max_concurrent: int = 3,
) -> list[dict]:
    semaphore = asyncio.Semaphore(max_concurrent)
    results = []

    async with httpx.AsyncClient(timeout=10.0) as client:
        async def _fetch_one(i: int) -> dict:
            async with semaphore:
                start = time.perf_counter()
                response = await client.get(url)
                elapsed = time.perf_counter() - start
                return {"index": i, "status": response.status_code, "elapsed": round(elapsed, 3)}

        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(_fetch_one(i)) for i in range(count)]
        results = [t.result() for t in tasks]
    return results
```

Test with 10 requests, max 3 concurrent:

```python
# Add to __main__
start = time.perf_counter()
limited_results = asyncio.run(fetch_rate_limited(url, count=10, max_concurrent=3))
limited_total = time.perf_counter() - start
print(f"Rate-limited (max 3): {len(limited_results)} requests in {limited_total:.2f}s")
```

Expected: ~5 seconds (10 requests / 3 concurrent = 4 rounds, each round costing one request's full latency - the 1s server delay plus round-trip). The semaphore prevents slamming the API while still maintaining concurrency.

### Step 4 - Add Retry Logic for Transient Failures

Create `src/capstone_ai/core/retry.py`:

```python
import asyncio
import logging
from collections.abc import Awaitable, Callable

import httpx

logger = logging.getLogger(__name__)


def _retry_after(response: httpx.Response, fallback: float) -> float:
    """A 429 often tells you exactly how long to wait. Honour it when it does."""
    header = response.headers.get("retry-after", "")
    return float(header) if header.isdigit() else fallback


async def with_retry(
    fn: Callable[..., Awaitable[httpx.Response]],
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    retryable_status: tuple[int, ...] = (429, 500, 502, 503),
    **kwargs,
) -> httpx.Response:
    for attempt in range(max_retries + 1):
        try:
            response = await fn(*args, **kwargs)
            response.raise_for_status()  # turn 429/5xx into an exception
            return response
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in retryable_status:
                raise  # 401, 404, 422 - retrying will never help
            if attempt == max_retries:
                raise  # out of attempts - surface the real error
            delay = _retry_after(exc.response, base_delay * 2**attempt)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            if attempt == max_retries:
                raise
            delay = base_delay * 2**attempt
        logger.warning(
            "Attempt %d/%d failed, retrying in %.1fs",
            attempt + 1, max_retries + 1, delay,
        )
        await asyncio.sleep(delay)
    raise RuntimeError("unreachable")  # satisfies the type checker
```

The line that makes the whole thing work is `response.raise_for_status()`. httpx hands you a `429` as a perfectly ordinary, perfectly successful `Response` object - no exception is raised. If you don't explicitly ask it to raise, your `except` block never fires and your retry loop quietly retries nothing.

The `except` clauses are deliberately narrow. A bare `except Exception` will happily retry a `TypeError` in your own code four times with exponential backoff before finally reporting it - turning an instant, obvious bug into a slow, confusing one. Retry only what is genuinely transient: the statuses in `retryable_status`, timeouts, and transport errors. A `404` is not transient; let it propagate on the first attempt.

`_retry_after` honours the `retry-after` header when the server sends it. On a `429` the API frequently tells you exactly how long to back off; guessing with exponential backoff when you've been handed the answer is how you get rate-limited again. The official Anthropic SDK honours `retry-after` the same way.

Retry gets wired into the client in Step 5 and properly unit-tested in Stage 5 - no need to verify it on its own here.

> One limitation worth knowing about the implementation you just wrote: it only parses the integer form of the `Retry-After` header. A spec-legal `Retry-After: 2.5` or an HTTP-date both fall through to the guessed backoff, and there is no upper cap - a server sending `Retry-After: 3600` will make your client sleep for an hour. Production code caps it.

### Step 5 - Build the Reusable AsyncHTTPClient Class

Refactor the loose functions into a proper client class. Replace the contents of `http_client.py` - the measurement functions from Steps 1-3 (including Step 3's, if you did it) and the `__main__` block have done their job, and the class below is what the rest of the project imports. Note that after this rewrite `uv run python -m capstone_ai.core.http_client` prints nothing, and the Success Criteria still ask for a measured 5-concurrent timing - so make sure you recorded your numbers before overwriting:

```python
import asyncio
import logging
import time
from types import TracebackType

import httpx

from capstone_ai.core.retry import with_retry

logger = logging.getLogger(__name__)


class AsyncHTTPClient:
    def __init__(
        self,
        base_url: str = "",
        timeout: float = 30.0,
        max_concurrent: int = 5,
        max_retries: int = 3,
    ):
        self._base_url = base_url
        self._timeout = timeout
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._max_retries = max_retries
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "AsyncHTTPClient":
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._client:
            await self._client.aclose()

    def _require_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError(
                "AsyncHTTPClient must be used as an async context manager: "
                "`async with AsyncHTTPClient(...) as client:`"
            )
        return self._client

    async def get(self, url: str, **kwargs) -> httpx.Response:
        client = self._require_client()
        async with self._semaphore:
            return await with_retry(
                client.get, url, max_retries=self._max_retries, **kwargs
            )

    async def post(self, url: str, **kwargs) -> httpx.Response:
        client = self._require_client()
        async with self._semaphore:
            return await with_retry(
                client.post, url, max_retries=self._max_retries, **kwargs
            )

    async def get_many(self, urls: list[str]) -> list[httpx.Response]:
        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(self.get(url)) for url in urls]
        return [t.result() for t in tasks]
```

In `get()`, the semaphore sits on the outside and retry on the inside. One request holds one concurrency slot for its entire life, retries included - flip the order and a retrying request would release its slot mid-backoff, letting a new request in and pushing you over your intended concurrency exactly when the server is already complaining. The semaphore is also created once in `__init__`, not per request: a semaphore built inside `get()` would be a fresh one every call and would cap nothing.

### Step 6 - Productive Friction: Block the Event Loop (Optional - Recommended)

> **Optional, but recommended.** Nothing later depends on this step - skip it if you must. But blocking the event loop is the single most common async bug in AI applications, and seeing it happen once is worth more than reading about it.

This step is deliberately broken. Create a temporary test script:

```python
# blocking_demo.py (temporary, don't commit)
import asyncio
import time
import httpx


async def bad_example():
    async with httpx.AsyncClient() as client:
        # This BLOCKS the event loop
        time.sleep(3)
        response = await client.get("https://httpbingo.org/get")
        print(f"Got: {response.status_code}")


async def main():
    start = time.perf_counter()
    async with asyncio.TaskGroup() as tg:
        for _ in range(3):
            tg.create_task(bad_example())
    elapsed = time.perf_counter() - start
    print(f"Total: {elapsed:.2f}s (should be ~3s if truly concurrent, but isn't)")


asyncio.run(main())
```

Save it as **`blocking_demo.py`**, not `test_blocking.py`. Anything matching `test_*.py` gets collected by pytest, which imports the file - and since this script calls `asyncio.run()` at module level, `uv run pytest` would execute the whole thing, live HTTP included, during collection, then report `collected 0 items`.

Run it: `uv run python blocking_demo.py`

Observe: it takes ~9 seconds, not ~3. The `time.sleep(3)` blocks the event loop - all three tasks run sequentially despite being async.

Fix it: replace `time.sleep(3)` with `await asyncio.sleep(3)` and re-run. Now it takes ~3 seconds.

This is the most common async bug in AI applications: calling a synchronous function (database driver, file I/O, CPU-bound computation) inside an async context. Diagnose it by looking for any function call that doesn't have `await` in front of it and takes significant time.

Delete `blocking_demo.py` after the exercise.

### Step 7 - Commit

```bash
git add src/capstone_ai/core/http_client.py src/capstone_ai/core/retry.py
git commit -m "M3-stage-02: async HTTP client with rate limiting and retry"
```

---

## Success Criteria

You're done when:

- [x] `AsyncHTTPClient` class exists in `src/capstone_ai/core/http_client.py` with `__aenter__`/`__aexit__`, semaphore-based rate limiting, and retry logic
- [x] Running 5 concurrent requests completes in roughly a quarter to a fifth of the time of 5 sequential requests (measured, not guessed - expect ~4-4.5x against a public endpoint, closer to 5x locally)
- [x] Rate-limited mode (`max_concurrent=3`) correctly caps parallelism - 10 requests with max 3 concurrent takes ~4x a single request, not 10x *(optional - Step 3)*
- [ ] You can explain the blocking event loop bug from Step 6 and how to fix it *(optional - Step 6)*
- [x] Changes are committed to git

## Quality Checklist (Best Practices Ownership)

- [ ] **Resource management:** `AsyncClient` is used with `async with` - never left unclosed
- [ ] **Timeouts configured:** Every client has an explicit timeout (not relying on defaults)
- [ ] **Rate limiting present:** Semaphore prevents unbounded concurrency - created once at client init, not per-request
- [ ] **Retry logic:** Transient failures (429, 5xx) are retried with exponential backoff; non-transient ones (404, 401) fail immediately
- [ ] **Error handling:** `TaskGroup` surfaces all failures (no silently swallowed exceptions)
- [ ] **No blocking calls:** No `time.sleep()`, `requests.get()`, or other synchronous I/O inside async functions

## Explain It Back

Answer in writing (3-5 sentences):

1. Why does `asyncio.TaskGroup` replace the older `asyncio.gather()` pattern? What happens when one task in a `TaskGroup` fails?

TaskGroup cancels all sibling tasks and raises an ExceptionGroup when one fails, instead of gather()'s leaked, unmanaged background tasks.


2. Suppose your tier allows 1,000 requests per minute and 2 million input tokens per minute, and your prompts average 20,000 input tokens. Which limit do you hit first, and how would you configure `AsyncHTTPClient` to stay under it? Is a semaphore sufficient, or do you need something more?

Token limit hits first (100 req/min vs 1,000 req/min cap); a semaphore alone isn't enough — you need a token-bucket rate limiter tracking tokens/min, with a semaphore only bounding concurrency.

3. What's the difference between `time.sleep()` and `await asyncio.sleep()` at the event loop level?

time.sleep() blocks the whole thread/event loop; await asyncio.sleep() yields control so other tasks can run.

## Stretch Goals

- **Streaming support:** Add a `stream_get()` method that yields response chunks using `httpx`'s async streaming. This prepares you for LLM streaming in Stage 3.
- **Connection pooling inspection:** Use `httpx`'s connection pool limits (`limits=httpx.Limits(max_connections=10)`) and observe connection reuse with logging.
- **Token bucket rate limiter:** Replace the semaphore with a proper token bucket that enforces requests-per-minute, not just max-concurrent.

## Common Pitfalls

| Problem | What You See | Recovery |
|---|---|---|
| `RuntimeError: no running event loop` | Calling `await` outside `asyncio.run()` | Wrap your entry point with `asyncio.run(main())`. |
| `ExceptionGroup` with multiple errors | Several tasks failed inside `TaskGroup` | Read all errors in the group. Fix the root cause (usually a timeout or connection error). |
| Slow despite being async | Same wall time as sync | Check for blocking calls (`time.sleep`, synchronous HTTP, CPU-bound code). Use `asyncio.to_thread()` for unavoidable sync work. |
| `httpx.PoolTimeout` | Too many concurrent requests | Lower `max_concurrent` or increase `httpx.Limits(max_connections=...)`. |
| Forgotten `await` | Coroutine object returned instead of result | Python warns: "coroutine was never awaited". Add `await` before the call. |

## Connection to Next Stage

You now have a robust async HTTP layer. In Stage 3, you'll discover that the Anthropic Python SDK uses httpx under the hood - your `AsyncHTTPClient` patterns (connection management, timeouts, concurrency) translate directly to `AsyncAnthropic` client usage. The rate limiting and retry logic you built here will inform how you handle Anthropic API limits.
