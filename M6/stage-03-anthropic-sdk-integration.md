# Stage 3 - Anthropic SDK Integration

**Lesson:** 3 of 5 (Anthropic SDK Deep Dive)
**Prerequisites:** Stages 1-2 complete - working project with async HTTP client layer, `.env` with Anthropic API key

## Context

In M1 you used the Anthropic API as a tourist - basic message calls to see what Claude can do. Now you're building your production home. This stage integrates the Anthropic Python SDK at depth: async client, streaming, tool use (the full loop), structured output extraction, and prompts versioned as Git artifacts.

The client wrapper you build here is the AI core of your capstone.

---

## Steps

### Step 1 - Initialize the Anthropic Client Wrapper

Create `src/capstone_ai/core/ai_client.py`:

```python
import anthropic
from capstone_ai.core.config import settings


def first_text(content: list) -> str:
    """Return the first text block's text, skipping thinking and tool_use blocks."""
    for block in content:
        if block.type == "text":
            return block.text
    return ""


class AIClient:
    def __init__(self):
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = settings.model_name
        self._max_tokens = settings.max_tokens

    async def message(self, user_message: str, system: str = "") -> str:
        params: dict = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": [{"role": "user", "content": user_message}],
        }
        if system:
            params["system"] = system
        response = await self._client.messages.create(**params)
        return first_text(response.content)

    async def close(self):
        await self._client.close()
```

**Why `first_text()` and not `response.content[0].text`?** Because `content[0]` is not
reliably the text. Read the next section before you go further - indexing into `content`
is the most common way this stage breaks.

Test it immediately:

```bash
uv run python -c "
import asyncio
from capstone_ai.core.ai_client import AIClient

async def main():
    client = AIClient()
    try:
        result = await client.message('Say hello in exactly 5 words.')
        print(f'Response: {result}')
    finally:
        await client.close()

asyncio.run(main())
"
```

If you see `TypeError: Could not resolve authentication method. Expected one of api_key, auth_token, or credentials to be set.` - **that is the no-key case, and it is the most likely one.** Stage 1 defaults `anthropic_api_key` to an empty string, so if `.env` is missing or unread the SDK gets `""` and refuses before making any request. Check that `.env` exists, holds a real key, and that `load_dotenv()` ran.

If you see `AuthenticationError` (401), the key was *present but rejected* - a typo, a revoked key, or the wrong workspace. If you see `APIConnectionError`, check your internet connection.

**What you actually got back**

`message()` returns a string, but it has to *find* that string. Every later step in this
stage depends on understanding why:

- The SDK hands you a `Message` object, not a dict. It deserializes the JSON for you, which is why you get attribute access and editor autocomplete instead of `response["content"][0]["text"]`.
- `content` is a list of content blocks, not a string. One response can carry `thinking`, `text`, and `tool_use` blocks side by side, and the order is not yours to choose.
- `response.usage` is your cost counter. `input_tokens` and `output_tokens` come back on every call, whether you look at them or not.

**The `content[0]` trap**

Most tutorials - and probably your own first draft - reach for `response.content[0].text`.
On Claude Sonnet 5 that line raises:

```
AttributeError: 'ThinkingBlock' object has no attribute 'text'
```

Sonnet 5 has adaptive thinking on by default. The model does not switch reasoning on or
off per request - it modulates how much reasoning each request gets. When reasoning shows
up in the response, it arrives as a `ThinkingBlock` **first** in the list, so `content[0]`
is the thinking block and `content[1]` is your answer. On other requests there is no
thinking block and `content[0]` *is* the answer. The position of the text block is not
stable.

The failure is not always a crash, either. By default the API returns thinking blocks
with their text omitted - `block.thinking` is an empty string - so code that grabs the
first block and displays whatever it holds does not raise; it shows an empty answer.
`content[0].text` crashes; `content[0]` handled generically just looks blank. Both are
the same bug.

This is why `first_text()` selects **by type, never by position**, and why Step 4's tool
loop iterates `response.content` checking `block.type`. Same rule everywhere: ask what a
block *is*, not where it sits.

Look at all of it once, directly, before you go back to working through the wrapper:

```bash
uv run python -c "
import asyncio, anthropic
from capstone_ai.core.config import settings

async def main():
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    r = await client.messages.create(
        model=settings.model_name, max_tokens=1024,
        messages=[{'role': 'user', 'content': 'Say hello in exactly 5 words.'}],
    )
    print(f'type:        {type(r).__name__}')
    print(f'content:     list of {len(r.content)} block(s) -> {[b.type for b in r.content]}')
    print(f'stop_reason: {r.stop_reason}')
    print(f'usage:       in={r.usage.input_tokens} out={r.usage.output_tokens}')
    for i, b in enumerate(r.content):
        print(f'  content[{i}].type = {b.type}')
    await client.close()

asyncio.run(main())
"
```

Note `max_tokens=1024`, not 64. **Thinking tokens count against `max_tokens`**, so a
small ceiling can be spent entirely on reasoning - you get `stop_reason='max_tokens'` and
no text block at all. That is not a bug in your code; it is a budget you set too low.

This probe goes straight to the SDK rather than through `AIClient` on purpose - it is a
throwaway, not something to keep. Production code reaches for the wrapper; exploration
reaches for the raw object.

### Step 2 - Add Multi-Turn Conversation Support (Optional)

> **Optional.** Read the key insight at the end of this step even if you skip the code - the API being stateless is something every later module assumes you know. Nothing downstream requires the `conversation()` method itself; the one Stage 5 unit-test class that covers it is optional too.

Extend `AIClient` with message history management:

```python
async def conversation(
    self,
    messages: list[dict],
    system: str = "",
) -> anthropic.types.Message:
    params: dict = {
        "model": self._model,
        "max_tokens": self._max_tokens,
        "messages": messages,
    }
    if system:
        params["system"] = system
    return await self._client.messages.create(**params)
```

Test multi-turn:

```python
messages = [
    {"role": "user", "content": "My name is Alice."},
    {"role": "assistant", "content": "Hello Alice! How can I help you today?"},
    {"role": "user", "content": "What's my name?"},
]
response = await client.conversation(messages)
# Claude should respond with "Alice"
```

Key insight: message history is your responsibility. The API is stateless - every call includes the full conversation. This means history management, truncation for long conversations, and cost awareness (every message in history costs tokens) are your problems to solve.

### Step 3 - Implement Streaming

Add a streaming method that yields text chunks as they arrive:

```python
from collections.abc import AsyncIterator


async def stream_message(
    self,
    user_message: str,
    system: str = "",
) -> AsyncIterator[str]:
    params: dict = {
        "model": self._model,
        "max_tokens": self._max_tokens,
        "messages": [{"role": "user", "content": user_message}],
    }
    if system:
        params["system"] = system

    async with self._client.messages.stream(**params) as stream:
        async for text in stream.text_stream:
            yield text
```

Test streaming visually:

```python
async def main():
    client = AIClient()
    try:
        async for chunk in client.stream_message("Explain async/await in Python in 3 sentences."):
            print(chunk, end="", flush=True)
        print()
    finally:
        await client.close()
```

Watch the text appear incrementally. This is what users see in chat interfaces - the progressive reveal. Your FastAPI server (Stage 4) will pipe these chunks as Server-Sent Events.

### Step 4 - Implement Tool Use

This is the most complex SDK feature. The flow is: define tools -> send message -> Claude responds with `tool_use` -> you execute the tool -> send `tool_result` back -> Claude synthesizes.

Add tool support to `AIClient`. Note the `logger.debug` calls - the loop is the one place in this stage where several API round-trips happen behind a single method call, and without them you see only the final string and have no way to tell what happened in between:

```python
import json
import logging

logger = logging.getLogger(__name__)


async def tool_conversation(
    self,
    messages: list[dict],
    tools: list[dict],
    tool_handler: dict,
    system: str = "",
    max_tool_rounds: int = 5,
) -> str:
    params: dict = {
        "model": self._model,
        "max_tokens": self._max_tokens,
        "messages": list(messages),
        "tools": tools,
    }
    if system:
        params["system"] = system

    for round_num in range(1, max_tool_rounds + 1):
        response = await self._client.messages.create(**params)
        logger.debug("tool round %d: stop_reason=%s", round_num, response.stop_reason)

        # Loop ONLY on tool_use. Every other stop_reason is terminal.
        if response.stop_reason != "tool_use":
            text_blocks = [b.text for b in response.content if b.type == "text"]
            return "\n".join(text_blocks)

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                handler = tool_handler.get(block.name)
                if handler:
                    result = await handler(block.input)
                else:
                    result = f"Error: unknown tool '{block.name}'"
                logger.debug("tool %s(%s) -> %s", block.name, json.dumps(block.input), result)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result),
                })

        params["messages"].append({"role": "assistant", "content": response.content})
        params["messages"].append({"role": "user", "content": tool_results})

    return "Max tool rounds exceeded"
```

Use `logger.debug` rather than `print` in library code like this. A `print` buried inside
a library method is not something a caller can turn off; logging is off by default and
costs the caller one line to switch on, which is what the test below does.

The loop continues on `stop_reason == "tool_use"` and returns on everything else. Writing
it the other way round - `if stop_reason == "end_turn": return` - looks equivalent and is
not, because `tool_use` and `end_turn` are not the only two values. `max_tokens`,
`stop_sequence`, `refusal` and `pause_turn` are all reachable, and each one would fall
through to the tool-handling branch below. With no `tool_use` blocks to process,
`tool_results` stays empty, you send `{"role": "user", "content": []}`, and the API
rejects it - so a truncated answer surfaces as a confusing validation error instead of a
short answer.

`max_tokens` is the one you will actually hit: thinking tokens count against the same
budget, so a reasoning-heavy tool round can exhaust `max_tokens` before Claude emits any
tool call. Enumerate what continues the loop and treat the rest as terminal.

Define a sample tool and handler, then test. Put the `await` call inside an
`async def main()` that constructs `AIClient` and closes it, like the test harness in
Step 1:

```python
import json
import logging

logging.basicConfig(level=logging.DEBUG)  # so the loop's trace is visible

TOOLS = [
    {
        "name": "get_weather",
        "description": "Get the current weather for a city",
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
    city = params["city"]
    # Simulated weather data
    return json.dumps({"city": city, "temp_c": 22, "condition": "sunny"})


tool_handler = {"get_weather": handle_weather}

result = await client.tool_conversation(
    messages=[{"role": "user", "content": "What's the weather in Tel Aviv?"}],
    tools=TOOLS,
    tool_handler=tool_handler,
)
print(result)
```

Verify: Claude calls `get_weather`, your handler returns the simulated data, Claude synthesizes a human-readable response mentioning 22 degrees and sunny.

Read the trace, not just the answer. You should see the cycle turn over:

```
DEBUG:capstone_ai.core.ai_client:tool round 1: stop_reason=tool_use
DEBUG:capstone_ai.core.ai_client:tool get_weather({"city": "Tel Aviv"}) -> {"city": "Tel Aviv", "temp_c": 22, "condition": "sunny"}
DEBUG:capstone_ai.core.ai_client:tool round 2: stop_reason=end_turn
```

Round 1 stops on `tool_use` - Claude has asked for something and is waiting. Your handler runs. Round 2 stops on `end_turn` - Claude has the result and can answer. If you only ever look at the returned string, you cannot tell a working loop from one that silently gave up.

`basicConfig(level=DEBUG)` turns on debug logging for *every* library, so you will also see lines from `asyncio` and `httpx`. Yours are the ones tagged with your own module name - which is the argument for `logging.getLogger(__name__)` over a bare print in the first place.

If Claude doesn't call the tool, your tool definition may be unclear. Check that the `description` field explains when to use it - the trace will show a single round ending in `end_turn`, with no tool line between.

The SDK also ships `client.beta.messages.tool_runner(...)`, which runs this whole loop for you - you hand it tools and callables, it handles the round-trips and the message threading. Build the loop by hand here so you understand what a helper like that automates and can judge one when you meet it.

### Step 5 - Extract Structured Output

Use tool use as a structured extraction pattern. Define a "schema" tool that forces Claude to return typed JSON. Put the model and the tool definition at module level in `ai_client.py`, above the class:

```python
from pydantic import BaseModel


class MeetingSummary(BaseModel):
    title: str
    date: str
    attendees: list[str]
    action_items: list[str]
    key_decisions: list[str]


EXTRACT_MEETING_TOOL = {
    "name": "extract_meeting_data",
    "description": "Extract structured meeting data from text. Always use this tool to return meeting information.",
    "input_schema": MeetingSummary.model_json_schema(),
}


async def extract_structured(
    self,
    text: str,
    tool_schema: dict,
    model_class: type[BaseModel],
) -> BaseModel:
    response = await self._client.messages.create(
        model=self._model,
        max_tokens=self._max_tokens,
        tools=[tool_schema],
        tool_choice={"type": "tool", "name": tool_schema["name"]},
        messages=[{"role": "user", "content": text}],
    )
    for block in response.content:
        if block.type == "tool_use":
            return model_class.model_validate(block.input)
    raise ValueError("No tool use block in response")
```

Test with a meeting transcript, inside your `main()` from Step 1:

```python
transcript = """
Team standup March 15. Alice, Bob, and Carol attended.
We decided to switch from REST to GraphQL for the internal API.
Action items: Alice will draft the GraphQL schema by Friday.
Bob will benchmark query performance. Carol updates the documentation.
"""

summary = await client.extract_structured(
    transcript, EXTRACT_MEETING_TOOL, MeetingSummary
)
print(summary.model_dump_json(indent=2))
```

Verify: the output is a valid `MeetingSummary` with populated fields. Pydantic validation catches malformed responses automatically.

**Your generated schema has no descriptions**

Print `MeetingSummary.model_json_schema()` and look at what Claude actually receives:

```json
"attendees": {"items": {"type": "string"}, "title": "Attendees", "type": "array"}
```

A type and an auto-titled name - no `description` anywhere. Descriptions are how Claude
decides what to put where, and `model_json_schema()` emits none of them unless you ask.
That is the gap between a schema that validates and a schema that communicates.

Fix it at the source, with `Field`:

```python
from pydantic import BaseModel, Field


class MeetingSummary(BaseModel):
    title: str = Field(description="Short meeting title, e.g. 'Q3 Planning Standup'")
    date: str = Field(description="Meeting date in ISO format (YYYY-MM-DD)")
    attendees: list[str] = Field(description="Full names of people who attended")
    action_items: list[str] = Field(description="One entry per commitment, prefixed with the owner's name")
    key_decisions: list[str] = Field(description="Decisions reached, excluding items still under discussion")
```

Re-run the extraction and compare. `date` in particular tends to come back as
`"March 15"` without the description and `"2026-03-15"` with it - the schema said `str`
either way, so Pydantic was never going to catch the difference. The descriptions are
part of the contract Claude works from.

Newer SDK versions also have native structured output: `client.messages.parse(...,
output_format=MeetingSummary)` takes your Pydantic model directly and returns a response
whose `parsed_output` is a validated instance. The tool-based version you are building
here works everywhere - it is the pattern you will meet in existing codebases, and the
only one that works when extraction has to share a call with real tools. Reach for
`parse()` when you write greenfield extraction and nothing else needs the tool slot.

### Step 6 - Version Prompts as Git Artifacts (Optional)

> **Optional.** Nothing downstream requires the prompt loader - Stage 5's tests deliberately pass `system` explicitly so they don't depend on it. The principle is the takeaway: prompts are code, and they belong in version control. If you skip the build, carry the principle into your capstone anyway.

Prompts are code. They deserve version control, review, and change tracking.

Create the prompts directory structure:

```bash
mkdir -p src/capstone_ai/prompts
```

Create your first versioned prompt file `src/capstone_ai/prompts/system_default.txt`:

```
You are a helpful AI assistant for the capstone project.
Respond concisely and accurately.
When you don't know something, say so clearly.
Always provide code examples when explaining technical concepts.
```

Create a prompt loader in `src/capstone_ai/core/prompt_loader.py`:

```python
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text().strip()
```

Update `AIClient.message()` so it falls back to the default prompt file when no system
prompt is passed. This is the complete method after the change - replace the Step 1
version with it:

```python
from capstone_ai.core.prompt_loader import load_prompt


async def message(self, user_message: str, system: str = "") -> str:
    if not system:
        system = load_prompt("system_default.txt")
    params: dict = {
        "model": self._model,
        "max_tokens": self._max_tokens,
        "messages": [{"role": "user", "content": user_message}],
        "system": system,
    }
    response = await self._client.messages.create(**params)
    return first_text(response.content)
```

The default is loaded at call time, and `system` is now always non-empty, so it goes
straight into `params`. Keep it this simple - explicit code here is easy to test later.

Commit the prompt files alongside code. When prompts change, the diff is visible in PRs - reviewable, discussable, revertable.

### Step 7 - Productive Friction: Broken Tool Definition (Optional)

> **Optional.** Nothing later depends on this exercise. Its lesson is stated below - tool schemas are hints the model may ignore, so handlers must validate their own input - but running the broken version yourself is what makes the lesson stick.

Intentionally break a tool definition and debug it.

Modify the `get_weather` tool schema - vague out the description, drop the parameter description, and remove the `required` field:

```python
BROKEN_TOOLS = [
    {
        "name": "get_weather",
        "description": "Get weather",  # too vague
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string"},  # no description
            },
            # "required" missing
        },
    }
]
```

Try calling it. Observe: Claude may not call the tool at all (description too vague), or may call it without the `city` parameter.

**Two things to know before you run it.** First, if Claude does omit `city`, your Step 4 handler does `params["city"]` and dies with an unhandled `KeyError` that propagates out of `tool_conversation` and kills the script - so wrap the handler defensively before you experiment, or you will be debugging your own crash instead of observing the model.

Second, and this is the real lesson: **putting `required` back does not prevent it.** Nothing client-side enforces that schema. `required` is a *hint carried to the model*, not a contract the SDK validates - the API will happily hand you tool input that violates your own schema. Fix each issue one at a time and re-test, then draw the right conclusion.

Tool definitions are specifications you are *asking* the model to honour, not constraints the runtime enforces. Vague descriptions, missing required fields, and undescribed parameters all make tool use less reliable - and because none of it is enforced, **your handler must validate its own input.** That is the habit this exercise is really teaching.

### Step 8 - Commit

```bash
git add src/capstone_ai/core/ai_client.py
# If you did the optional Step 6, also add the prompt loader and prompt files:
git add src/capstone_ai/core/prompt_loader.py src/capstone_ai/prompts/
git commit -m "M3-stage-03: Anthropic SDK client with streaming, tool use, structured extraction"
```

---

## Success Criteria

You're done when:

- [x] `AIClient` class handles basic messages, streaming, tool use, and structured extraction
- [ ] **No content block is accessed by index.** Every read of `response.content` selects by `block.type`
- [ ] Streaming works: text chunks arrive incrementally (not all at once)
- [ ] Tool use completes the full cycle: Claude calls tool -> handler runs -> result returned -> Claude synthesizes, and the debug trace shows `stop_reason` going `tool_use` -> `end_turn`
- [ ] The tool loop continues on `tool_use` and treats every other `stop_reason` as terminal
- [ ] Structured extraction returns a valid Pydantic model from unstructured text
- [ ] Multi-turn conversation passes full message history and Claude remembers earlier turns *(optional - Step 2)*
- [ ] Prompts are stored in `src/capstone_ai/prompts/` and loaded by the client *(optional - Step 6)*
- [ ] Changes are committed to git

## Quality Checklist (Best Practices Ownership)

- [ ] **Async client:** Using `AsyncAnthropic`, not the sync `Anthropic` client
- [ ] **Resource cleanup:** Client has a `close()` method and/or is used with async context manager patterns
- [ ] **Tool use safety:** Tool execution loop has a `max_tool_rounds` cap to prevent infinite loops
- [ ] **Structured validation:** Pydantic validates all structured output - malformed responses are caught
- [ ] **Prompt versioning:** Prompts live in files, not hardcoded strings; changes are visible in git diffs *(optional - Step 6)*
- [ ] **Error handling:** API errors (auth, rate limit, server error) produce clear messages, not raw stack traces

## Explain It Back

Answer in writing (3-5 sentences):

1. Walk through the tool use cycle: what happens at each step, and why can't Claude execute the tool itself?

Claude picks a tool and returns a tool_use block → your code executes the actual function → you send the result back as a tool_result → Claude continues — Claude can't execute it itself because it has no runtime access to your systems, only the ability to describe what to call.


2. Step 5 forces the extraction tool with `tool_choice`. What would change if you left tool choice to Claude, and when is leaving it to Claude the right call?

Leaving tool_choice to auto lets Claude reply in plain text instead of always calling the tool, which is right for conversational/optional-tool cases but wrong here since you always want a MeetingSummary back.

3. Why store prompts as files in Git instead of as strings in your Python code? *(Answer this even if you skipped the optional Step 6 - the principle is the point.)*

Prompts as files let you diff, review, and version prompt changes independently of code changes, and let non-engineers edit them without touching Python.





## Stretch Goals

- **Multi-tool conversation:** Define 3 tools (weather, calculator, database lookup). Send a message that requires Claude to call multiple tools in sequence to answer.
- **Streaming with tool use:** Implement streaming that also handles tool use blocks mid-stream.
- **Prompt template system:** Add Jinja2 or string template support to the prompt loader for parameterized prompts.

## Common Pitfalls

| Problem | What You See | Recovery |
|---|---|---|
| `TypeError: Could not resolve authentication method` | Raised at call time, before any request | No key at all - Stage 1 defaults it to `""`. Check `.env` exists and `load_dotenv()` ran. **This, not `AuthenticationError`, is what an unset key looks like.** |
| `AuthenticationError` | 401 response from API | The key was sent and rejected - typo, revoked, or wrong workspace. |
| Tool not called | Claude responds with text instead of `tool_use` | Make your tool `description` more specific. Add "Always use this tool when..." |
| Infinite tool loop | `max_tool_rounds` exceeded | Check that your tool handler returns a useful result. Claude keeps calling tools if results are unhelpful. |
| `AttributeError: 'ThinkingBlock' object has no attribute 'text'` | Any use of `response.content[0].text` - or an answer that displays as empty, since a thinking block's text is empty by default | Sonnet 5 often puts a `thinking` block first. Select by type with `first_text()`, never by index. |
| Pydantic validation error | Structured extraction fails on Claude's output | Read *which field* failed. It is nearly always a required field Claude omitted or typed differently - give it a `Field(description=...)` so the schema tells Claude what you want, or relax the type. Note that `model_config = {"extra": "ignore"}` does **not** help: ignoring extras is already Pydantic v2's default, so it cannot fix a validation error. |

## Connection to Next Stage

You have a powerful Anthropic client - but it lives in a script. In Stage 4, you wrap it in a FastAPI server so any frontend, mobile app, or other service can talk to your AI through HTTP. The streaming method becomes SSE endpoints. The tool use method becomes a REST call. The structured extraction powers typed API responses.
