# Stage 4 - FastAPI Server

**Lesson:** 4 of 5 (FastAPI for AI Apps)
**Prerequisites:** Stages 1-3 complete - working project with Anthropic client wrapper (streaming, tool use), async HTTP layer, `.env` with API key

## Context

Your Anthropic client is powerful but trapped in a script. No user can reach it. In this stage, you wrap it in a FastAPI server - the HTTP interface that turns your AI capabilities into an API anyone can call. You'll build chat endpoints, streaming via Server-Sent Events, tool-augmented queries, and the middleware that makes it production-grade.

FastAPI is the natural choice: it's async-native (no awkward wrapping of your async client), has built-in Pydantic integration (your request/response models validate automatically), and generates API documentation for free.

---

## Steps

### Step 1 - Minimal FastAPI App with Health Check

Create `src/capstone_ai/api/main.py`:

```python
from fastapi import FastAPI

app = FastAPI(title="Capstone AI API", version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "ok"}
```

Start the server:

```bash
uv run uvicorn capstone_ai.api.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000/docs` in your browser. You should see the Swagger UI with the `/health` endpoint. Click "Try it out" and execute - you should get `{"status": "ok"}`.

**The `uv run` prefix is not optional.** A bare `uvicorn ...` uses whatever `uvicorn` is first on your `PATH` - often a system-wide one on a different Python that has never heard of `capstone_ai` - and dies with `ModuleNotFoundError: No module named 'capstone_ai'`. `uv run` resolves your project environment first. `--reload` works fine through it.

If you still see `ModuleNotFoundError` *with* `uv run`, then run `uv sync --extra server`: sync installs your own package in editable mode, so there is no separate install step. But note that sync will **not** fix the bare-`uvicorn` case above - that is a `PATH` problem, not a missing package.

### Step 2 - Define Pydantic Request/Response Models

Create `src/capstone_ai/api/models.py`:

```python
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    system: str = Field(default="", max_length=5000)


class ChatResponse(BaseModel):
    response: str
    model: str
    usage: dict | None = None


class ToolRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    system: str = Field(default="", max_length=5000)


class ErrorResponse(BaseModel):
    error: str
    detail: str = ""
```

These models give you automatic request validation (reject malformed input before it hits Claude), typed responses (clients know exactly what to expect), and free API documentation (Swagger UI renders the schemas).

### Step 3 - Add the Chat Endpoint

Update `main.py` to wire the Anthropic client into a chat endpoint:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException

from capstone_ai.core.ai_client import AIClient
from capstone_ai.core.config import settings
from capstone_ai.api.models import ChatRequest, ChatResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.ai_client = AIClient()
    yield
    await app.state.ai_client.close()


app = FastAPI(title="Capstone AI API", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        result = await app.state.ai_client.message(
            request.message, system=request.system
        )
        return ChatResponse(response=result, model=settings.model_name)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
```

The lifespan context manager creates the `AIClient` once at startup and closes it on shutdown. Creating a client inside the handler would mean a new connection pool on every request - with 100 concurrent users, that's 100 connection pools fighting for sockets. `app.state` is FastAPI's built-in way to share objects like this across request handlers without globals.

Errors from the Anthropic API map to 502 (upstream failure), not 500 (a bug in your code). The distinction tells whoever is on call where to look: a 502 points at Anthropic's status page, a 500 points at your handler.

The `model` field reports `settings.model_name` - the model comes from settings (or from the API response), never a hardcoded literal, so the response contract stays accurate for every client that reads it.

`usage` stays `None` for now. `AIClient.message()` returns a bare `str`, so the token counts genuinely are not available at this layer - the information was thrown away one level down. An API can only be as truthful as the layer beneath it. Wiring `response.usage` up from Stage 3 is a stretch goal below.

Test in Swagger UI: POST to `/chat` with `{"message": "Hello, what can you do?"}`. Then send `{"message": ""}` - Pydantic rejects it with a 422 before your handler code ever runs.

### Step 4 - Add Streaming via Server-Sent Events

Add the streaming endpoint to `main.py`. All routes live in `main.py` - Stage 5's tests import the app with `from capstone_ai.api.main import app`.

```python
from fastapi.responses import StreamingResponse


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    async def event_generator():
        try:
            async for chunk in app.state.ai_client.stream_message(
                request.message, system=request.system
            ):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            yield f"data: [ERROR] {exc}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
```

Test streaming with curl (not Swagger - Swagger can't render SSE progressively):

```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Count from 1 to 10 slowly."}'
```

You should see `data: ` lines appearing incrementally. The `-N` flag disables curl's output buffering so you see chunks in real-time.

If the response arrives all at once, check that the `Cache-Control: no-cache` header is set and that your generator yields per chunk instead of accumulating everything first. (Step 8 digs into what `media_type` does and does not control here.)

### Step 5 - Add Tool-Use Endpoint (Optional)

> **Optional.** This is thin wiring over Stage 3's `tool_conversation` - little new FastAPI learning beyond what `/chat` already taught you. If you skip it, also skip the `TestToolsEndpoint` class in Stage 5 and read the conditional notes in Steps 6-7 below.

Wire the tool conversation into an endpoint:

```python
import json
from capstone_ai.api.models import ToolRequest, ChatResponse


# Define tools and handlers at module level (or load from config)
TOOLS = [
    {
        "name": "get_weather",
        "description": "Get the current weather for a city. Use this when the user asks about weather.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name"},
            },
            "required": ["city"],
        },
    }
]


async def handle_weather(params: dict) -> str:
    return json.dumps({"city": params["city"], "temp_c": 22, "condition": "sunny"})


TOOL_HANDLERS = {"get_weather": handle_weather}


@app.post("/chat/tools", response_model=ChatResponse)
async def chat_with_tools(request: ToolRequest):
    try:
        result = await app.state.ai_client.tool_conversation(
            messages=[{"role": "user", "content": request.message}],
            tools=TOOLS,
            tool_handler=TOOL_HANDLERS,
            system=request.system,
        )
        return ChatResponse(response=result, model=settings.model_name)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
```

Test in Swagger UI: POST to `/chat/tools` with `{"message": "What's the weather in Paris?"}`.

### Step 6 - Add Middleware

Add cross-cutting concerns: request logging, error handling, and CORS.

```python
import logging
import time
import uuid

from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start = time.perf_counter()

        response = await call_next(request)

        elapsed = time.perf_counter() - start
        logger.info(
            "[%s] %s %s -> %d (%.3fs)",
            request_id, request.method, request.url.path,
            response.status_code, elapsed,
        )
        response.headers["X-Request-ID"] = request_id
        return response


# Add to app setup (after app = FastAPI(...)):
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)
```

One warning about the logging middleware: log metadata (method, path, status, timing), not request bodies. Bodies can contain sensitive data, and large payloads make logging slow.

Add a custom exception handler for Anthropic errors:

```python
from anthropic import APIError
from fastapi.responses import JSONResponse

from capstone_ai.api.models import ErrorResponse


@app.exception_handler(APIError)
async def anthropic_error_handler(request: Request, exc: APIError):
    return JSONResponse(
        status_code=502,
        content=ErrorResponse(error="AI service error", detail=str(exc)).model_dump(),
    )
```

Registering the handler is not enough. The `/chat` and `/chat/tools` endpoints from Steps 3 and 5 wrap the client call in `except Exception`, and `APIError` is a subclass of `Exception` - so each endpoint converts it to an `HTTPException` before it can ever reach the handler, and the structured JSON body above is never sent.

Let `APIError` through by narrowing the `except` in `/chat`:

```python
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        result = await app.state.ai_client.message(
            request.message, system=request.system
        )
        return ChatResponse(response=result, model=settings.model_name)
    except APIError:
        raise  # handled by anthropic_error_handler -> structured 502
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
```

Make the same change in `/chat/tools` (if you built the optional Step 5 endpoint): add the `except APIError: raise` clause above its `except Exception`. The `/chat/stream` generator is the one place this pattern does not apply - by the time an error happens inside the generator, the 200 status and headers are already on the wire, so no exception handler can produce a new response. That's why the generator surfaces errors as `data: [ERROR] ...` lines instead: it's the SSE equivalent of a structured error body.

Verify with real response bodies, not by reading the code. First trigger a validation error: POST `/chat` with `{"message": ""}` and read the 422 body Pydantic produces. Then trigger an upstream error: with a deliberately invalid key in `.env`, a request to `/chat` should return the handler's shape:

```json
{"error": "AI service error", "detail": "..."}
```

and not FastAPI's default `{"detail": "..."}`. If you see `{"detail": ...}`, your `except Exception` is still winning.

**Before you restart, add one line** near the top of `main.py`, or you will see nothing:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

`logging.getLogger(__name__)` sends records to the **root** logger, and uvicorn configures only
its own loggers - the root keeps its default WARNING threshold and no handler, so your INFO lines
are created and silently dropped. The middleware is running either way (every response carries an
`X-Request-ID`), which makes this a nasty one to debug: the feature works, the evidence is
invisible.

Restart the server and make a request. Now the terminal shows lines like:

```
INFO:capstone_ai.api.main:[e6cdbace] GET /health -> 200 (0.004s)
```

If you see the header but no log line, it is this.

### Step 7 - Add API Key Authentication

Add a simple header-based API key check using FastAPI dependencies:

```python
from fastapi import Depends, Security
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=True)


async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    expected = "dev-key-change-in-production"
    if api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key
```

Apply it to every chat endpoint you built:

```python
@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(verify_api_key)])
async def chat(request: ChatRequest):
    # ... existing implementation
```

Add the same `dependencies=[Depends(verify_api_key)]` to `/chat/stream` - and to `/chat/tools`, if you built it. Leave `/health` unprotected - load balancers need to probe it without credentials.

Do not skip the last part: if the dependency lands on `/chat` only, the other chat endpoints return 200 with no key at all - and those are the endpoints that actually spend tokens. Verify with `curl -o /dev/null -w '%{http_code}\n' -X POST localhost:8000/chat/stream -H 'Content-Type: application/json' -d '{"message":"hi"}'` - it should print 401. (You can also lift the dependency to the router/app level instead of repeating it per route.)

One more thing worth knowing before Stage 5: **auth runs before body validation.** A request with no key *and* an invalid body returns **401**, not 422 - the security dependency resolves first and short-circuits. Worth knowing before you write a test that expects 422 and sends no key.

Test: calling `/chat` without the `X-API-Key` header returns **401** (`{"detail": "Not authenticated"}`, raised by `APIKeyHeader` itself because `auto_error=True`). With a *wrong* key you get 401 from your own check above. With the correct header, it works. Expect 401 in both cases; very old FastAPI versions returned 403 for a missing header - if you see 403, check your version with `uv run python -c "import fastapi; print(fastapi.__version__)"`.

### Step 8 - Productive Friction: Broken SSE (Optional)

> **Optional.** Nothing later depends on this exercise. Its takeaway - `curl` proves the transport works but says nothing about the SSE contract, so test with an instrument that speaks the protocol - is worth reading even if you skip the run.

Intentionally break the streaming endpoint. Change the `media_type` to `"application/json"`:

```python
return StreamingResponse(
    event_generator(),
    media_type="application/json",  # wrong!
)
```

Test with curl:

```bash
curl -sN localhost:8000/chat/stream -H 'Content-Type: application/json' \
  -d '{"message": "Count to five"}'
```

**Observe carefully, because the interesting thing here is what does *not* happen.** The chunks still arrive one at a time, at exactly the same cadence as before. `curl -sI` still shows `transfer-encoding: chunked`. Nothing buffered, nothing broke. The *only* thing that changed is one header.

That is the lesson, and it is a better one than "wrong content type breaks streaming": `StreamingResponse` streams because of chunked transfer encoding, which is a **transport** concern. `media_type` is a **semantic** label telling the client how to interpret the bytes. They are independent, and curl - which interprets nothing - cannot tell the difference.

So who does break? The client that actually reads the label. A browser's `EventSource` **refuses a response whose content type is not `text/event-stream`**, firing `onerror` without delivering a single message. Your server looks perfectly healthy; the JavaScript sees nothing.

**The takeaway worth writing down:** `curl` proved the transport worked and told you nothing about whether the contract was right. A green result from the wrong instrument is not evidence. If you ship an SSE endpoint, test it with something that speaks SSE.

Fix it back to `"text/event-stream"` and re-test.

> Note that the broken snippet above also drops the `headers={...}` argument from your Step 4 version, taking `Cache-Control: no-cache` and `Connection: keep-alive` with it. Put those back too - proxies and some browsers buffer without them, which is a *real* way to break streaming and worth contrasting with the fake one you just tried.

Before moving on, think through what else could silently break SSE between your server and a browser: a reverse proxy buffering responses (nginx needs `proxy_buffering off`), a missing `Cache-Control: no-cache` header (proxies and CDNs may buffer the stream), an async generator that accumulates everything and yields once instead of yielding per chunk, and your own middleware - you added middleware in Step 6 and broke the SSE contract in Step 8, so when streaming misbehaves there are multiple candidate causes between the route and the client. `curl -N` strips away every intermediary and shows exactly what the server puts on the wire; a client that speaks SSE tells you whether the contract is right. You need both.

### Step 9 - Commit

Your final `main.py` should read top to bottom: imports, `lifespan`, `app = FastAPI(lifespan=lifespan)`, middleware registration (CORS, then `RequestLoggingMiddleware`), the `APIError` exception handler, the auth dependency, then the routes - `/health`, `/chat`, `/chat/stream`, and, if you built the optional Step 5, the tool definitions and `/chat/tools`. If yours is ordered differently it still works - FastAPI resolves everything at startup - but this order matches how the file grew and makes review easier.

```bash
git add src/capstone_ai/ tests/ pyproject.toml uv.lock
git commit -m "M3-stage-04: FastAPI server with chat, streaming, tool use, middleware"
```

---

## Success Criteria

You're done when:

- [x] `uv run uvicorn` starts the server and Swagger UI loads at `/docs`
- [x `/health` returns `{"status": "ok"}` without an API key
- [x] `/chat` accepts a message and returns a Claude response with Pydantic-validated request/response
- [x] `/chat/stream` returns Server-Sent Events that arrive incrementally (verified with `curl -N`)
- [x] `/chat/tools` triggers tool use and returns Claude's synthesis of the tool result *(optional - Step 5)*
- [x] All chat endpoints you built return 401 without a valid `X-API-Key` header
- [x] Request logging middleware prints timing and request IDs to the console
- [x] The Anthropic client is created once at startup (lifespan), not per-request
- [x] Changes are committed to git

## Quality Checklist (Best Practices Ownership)

- [ ] **Pydantic validation:** Every chat endpoint has typed request and response models - no raw dicts in the chat API contract
- [ ] **Error responses structured:** API errors return `{"error": "...", "detail": "..."}`, not raw stack traces
- [ ] **Streaming correct:** SSE endpoint uses `text/event-stream` content type and `no-cache` header
- [ ] **Client lifecycle:** `AIClient` created in lifespan, not per-request; properly closed on shutdown
- [ ] **CORS configured:** Cross-origin requests allowed (restrictable in production)
- [ ] **Health check present:** `/health` endpoint exists for load balancer probes and stays unauthenticated
- [ ] **Authentication exists:** Header-based API key check on every chat endpoint you built (`/chat`, `/chat/stream`, and `/chat/tools` if present)

## Explain It Back

Answer in writing (3-5 sentences):

1. Why does the `AIClient` live in `app.state` (created once at startup) instead of being created inside each endpoint handler?

It's created once because AI client setup (HTTP connection pooling, auth) is expensive and stateless-safe to share, so reusing one instance across requests avoids reconnecting/reauthenticating on every call.

2. What happens if you remove the `Cache-Control: no-cache` header from the streaming response? Why does this matter for SSE?


Without Cache-Control: no-cache, proxies/browsers may buffer or cache the stream, delaying or breaking delivery of the incremental SSE events instead of pushing them through immediately.

3. Describe the request lifecycle: request arrives -> middleware -> route -> dependency injection -> handler -> response. What does each layer do?

Middleware runs cross-cutting logic (auth, logging, CORS) on every request; routing matches the URL/method to a handler; dependency injection resolves and provides shared resources (like the AIClient) to that handler; the handler executes business logic and builds a response; that response then flows back out through the middleware chain to the client.


## Stretch Goals

- **Populate `usage`:** Change `AIClient.message()` to return the token counts alongside the text (a dict or a small dataclass) instead of a bare `str`, then fill in `ChatResponse.usage`. Every caller of `message()` has to change - which is the point: the return type of your lowest layer decides what every layer above it can report. Stage 5's optional TDD step builds a `TokenCounter` to track spend; wiring it into `AIClient` is much easier if the usage data already flows.
- **Client disconnect:** Close the `curl` mid-stream and watch the server. The Anthropic call keeps running and keeps billing, because nothing checks whether anyone is still listening. Add an `await request.is_disconnected()` check in the generator loop, or swap `StreamingResponse` for `sse-starlette`'s `EventSourceResponse`, which handles disconnects and keepalive pings for you.
- **WebSocket endpoint:** Add a `/chat/ws` WebSocket endpoint for bidirectional chat (SSE is unidirectional). Compare the tradeoffs.
- **Rate limiting middleware:** Add per-IP rate limiting using `slowapi` or a custom middleware with `asyncio.Semaphore`.
- **Structured logging:** Replace the plain `logging` calls with `structlog` or `python-json-logger` for JSON-formatted logs parseable by log aggregators.

## Common Pitfalls

| Problem | What You See | Recovery |
|---|---|---|
| `ModuleNotFoundError: capstone_ai` | Module not found at import | Run `uv sync --extra server` from the project root, or prefix the command with `uv run`. |
| Streaming arrives all at once | No progressive text display | Check the `Cache-Control: no-cache` header, any proxy in between, and that your generator yields per chunk. (A wrong `media_type` breaks SSE clients like `EventSource`, not curl - see Step 8.) |
| 502 on every request | `AIClient` fails to initialize | Check `.env` API key. Check lifespan creates the client before yield. |
| CORS errors in browser | Browser blocks cross-origin request | Verify `CORSMiddleware` is added to the app. Check `allow_origins`. |
| `uvicorn` won't start | Port already in use | Use a different port: `--port 8001`. Or kill the existing process: `lsof -i :8000`. |

## Connection to Next Stage

Your AI application now has an HTTP interface. Users can chat with Claude through your API, stream responses, and trigger tool use. But how do you know it actually works correctly? In Stage 5, you build the test harness: unit tests for the client, integration tests for the API, and an eval pattern for scoring non-deterministic AI output.
