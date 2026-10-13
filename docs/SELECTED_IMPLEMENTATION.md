# Selected Implementation

A handful of real fragments, not the full codebase, not the full system prompt, not the complete Terraform. Each one exists because of a specific failure, not as a general purpose utility.

## A hard boundary in code, not just a prompt instruction

The agent is told to ask before pulling a wide date range. That alone was not enough once a live test showed the model sweeping six dates on its own. The actual boundary lives in the tool itself.

```python
if span_days > MAX_RANGE_DAYS:
    raise InvalidToolArgument(
        f"date range spans {span_days} days, but at most "
        f"{MAX_RANGE_DAYS} days are allowed per call"
    )
```

## A time budget the agent checks before starting more work

Lambda has a hard execution ceiling. Rather than let a slow external call run past it and kill the whole response, each loop checks the remaining budget before starting another item and reports what it had to skip instead of silently dropping it.

```python
left = remaining_seconds()
if left is not None and left < _WORST_CASE_SECONDS_PER_DATE:
    skipped_dates.extend(
        (start + timedelta(days=o)).isoformat()
        for o in range(offset, span_days)
    )
    break
```

## Duplicate tool calls caught by the SDK's own hook, not a hand rolled loop

Strands exposes a real extension point for this. Using it, instead of writing a custom loop around the agent, keeps the SDK's own event loop as the single source of truth.

```python
def _on_before_tool_call(self, event: BeforeToolCallEvent) -> None:
    signature = (
        event.tool_use["name"],
        json.dumps(event.tool_use["input"], sort_keys=True),
    )
    if signature in self.state.executed_tools:
        event.cancel_tool = (
            "This exact tool call already ran earlier in this turn; "
            "reusing the previous result instead of calling it again."
        )
        return
```

## A boto3 client with no default trust

The default retry and timeout behavior of a boto3 client is not safe for a slow, expensive call. Without this, a client side read timeout silently re invoked the whole Lambda two or three more times, with no visibility into why the UI felt stuck.

```python
Config(retries={"max_attempts": 0}, read_timeout=70, connect_timeout=10)
```

`max_attempts` here means retry count, not total attempts. Zero means the client fails fast and visibly instead of quietly re eating the clock.

## The diagnostic script, not a fix

For the still open Lambda connectivity finding (see EVIDENCE.md), this is the actual script used to gather evidence from inside the real Lambda: one direct, non retried call, bypassing the agent and Bedrock entirely, reporting exactly what came back.

```python
def _diagnose_nba_connectivity() -> dict:
    from nba_api.stats.library.http import STATS_HEADERS
    from tools._nba_api_client import fetch_games

    result = {"headers_sent": dict(STATS_HEADERS)}
    start = time.monotonic()
    try:
        data = fetch_games("2026-10-06", 10)
        result["outcome"] = "success"
        result["games_returned"] = len(data["game_header"])
    except Exception as exc:
        result["outcome"] = "failed"
        result["exception_type"] = type(exc).__name__
        result["exception_message"] = str(exc)
        response = getattr(exc, "response", None)
        result["http_status"] = getattr(response, "status_code", None)
    result["elapsed_seconds"] = round(time.monotonic() - start, 2)
    return result
```

No fix shipped from this yet. It is included here because it is the method, not a finished answer, and the method is the part worth showing while the finding is still open.
