"""shim-engine core — recorder + context manager + decorator."""

from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from functools import wraps
from typing import Any, Callable, Dict, Iterator, List, Optional, Union

DEFAULT_LOG_PATH = os.environ.get("SHIM_ENGINE_LOG", "shim_engine.jsonl")
DEFAULT_COST_PER_M = float(os.environ.get("SHIM_ENGINE_COST_PER_M", "5.0"))

# Optional MLLANG awareness — graceful when absent.
try:
    from .mllang_adapter import extract_mllang_signals, mllang_available
except ImportError:  # pragma: no cover
    def mllang_available() -> bool:  # type: ignore[no-redef]
        return False

    def extract_mllang_signals(response_text: str) -> Optional[Dict[str, Any]]:  # type: ignore[no-redef]
        return None


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _estimate_tokens(text: str) -> int:
    """Best-effort token count. Uses tiktoken if installed, else 1 token ≈ 4 chars heuristic."""
    if not text:
        return 0
    try:
        import tiktoken  # type: ignore

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return max(1, len(text) // 4)


def _json_rpc_envelope_size(payload: Dict[str, Any]) -> int:
    """Estimate the JSON-RPC envelope size for the same content. Used as baseline for token-reduction comparison."""
    body = {
        "jsonrpc": "2.0",
        "method": "agent_state",
        "params": {k: v for k, v in payload.items() if v not in (None, "", [], {}, 0)},
    }
    return len(json.dumps(body, ensure_ascii=False))


@dataclass
class _Record:
    ts: str
    model: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    latency_s: float = 0.0
    cost_estimate_usd: float = 0.0
    response_chars: int = 0
    response_tokens_est: int = 0
    json_rpc_chars: int = 0
    json_rpc_tokens_est: int = 0
    tokens_saved_est: int = 0
    reduction_pct: float = 0.0
    halt: str = ""
    confidence: float = 0.0
    agent_code: str = ""
    slots_present: List[str] = field(default_factory=list)
    has_mllang_packet: bool = False
    tags: Dict[str, str] = field(default_factory=dict)
    parser: str = "none"


class Recorder:
    """Append-only JSONL recorder for a session of LLM calls."""

    def __init__(
        self,
        path: Optional[str] = None,
        parser: str = "none",
        cost_per_M: Optional[float] = None,
    ):
        self.path = path or DEFAULT_LOG_PATH
        self.parser = parser
        self.cost_per_M = cost_per_M if cost_per_M is not None else DEFAULT_COST_PER_M
        self._records_written = 0

    def observe(
        self,
        response: str = "",
        model: str = "",
        tokens_in: int = 0,
        tokens_out: int = 0,
        latency_s: float = 0.0,
        tags: Optional[Dict[str, str]] = None,
        parser: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record one LLM call.

        Args:
            response: text the model returned.
            model: model identifier (e.g. 'claude-opus-4-7').
            tokens_in / tokens_out: counts reported by the vendor SDK.
            latency_s: wall-clock seconds for this call.
            tags: free-form key/value tags (call_type, thread_id, etc.).
            parser: 'none' (default) or 'mllang' to attempt slot extraction
                from the response.

        Returns:
            The full record dict (also written to JSONL).
        """
        active_parser = parser if parser is not None else self.parser
        response = response or ""
        tags = tags or {}

        cost = ((tokens_in + tokens_out) / 1_000_000) * self.cost_per_M

        rec = _Record(
            ts=_now_iso(),
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_s=round(latency_s, 4),
            cost_estimate_usd=round(cost, 6),
            response_chars=len(response),
            response_tokens_est=_estimate_tokens(response),
            tags=tags,
            parser=active_parser,
        )

        if active_parser == "mllang" and response:
            signals = extract_mllang_signals(response)
            if signals is not None:
                rec.has_mllang_packet = True
                rec.halt = signals.get("halt", "")
                rec.confidence = signals.get("confidence", 0.0)
                rec.agent_code = signals.get("agent_code", "")
                rec.slots_present = signals.get("slots_present", [])
                json_rpc_size = signals.get("json_rpc_chars", 0)
                rec.json_rpc_chars = json_rpc_size
                rec.json_rpc_tokens_est = max(1, json_rpc_size // 4)
                rec.tokens_saved_est = max(
                    0, rec.json_rpc_tokens_est - rec.response_tokens_est
                )
                if rec.json_rpc_tokens_est > 0:
                    rec.reduction_pct = round(
                        100.0
                        * rec.tokens_saved_est
                        / rec.json_rpc_tokens_est,
                        1,
                    )

        out = asdict(rec)
        self._write(out)
        return out

    def _write(self, payload: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self._records_written += 1

    @property
    def records_written(self) -> int:
        return self._records_written


@contextmanager
def record(
    path: Optional[str] = None,
    parser: str = "none",
    cost_per_M: Optional[float] = None,
) -> Iterator[Recorder]:
    """Context manager. Yields a Recorder; call .observe(...) inside.

    Example:
        with record("calls.jsonl", parser="mllang") as r:
            r.observe(response=text, model="claude-opus", ...)
    """
    r = Recorder(path=path, parser=parser, cost_per_M=cost_per_M)
    try:
        yield r
    finally:
        pass


def observe(
    response: str = "",
    model: str = "",
    tokens_in: int = 0,
    tokens_out: int = 0,
    latency_s: float = 0.0,
    tags: Optional[Dict[str, str]] = None,
    parser: str = "none",
    path: Optional[str] = None,
) -> Dict[str, Any]:
    """One-shot helper — open a recorder, write one record, close.

    Convenient when you don't want to manage a context manager."""
    r = Recorder(path=path, parser=parser)
    return r.observe(
        response=response,
        model=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        latency_s=latency_s,
        tags=tags,
    )


def instrument(
    fn: Optional[Callable[..., Any]] = None,
    *,
    path: Optional[str] = None,
    parser: str = "none",
    extract: Optional[Callable[[Any], Dict[str, Any]]] = None,
):
    """Decorator that times the wrapped call and records the result.

    The decorated function should return either:
        - a string (the response text), or
        - a dict with keys {"response", "model", "tokens_in", "tokens_out"}, or
        - any object, paired with an `extract=` callable that returns
          the dict above.

    Example:
        @instrument(path="calls.jsonl", parser="mllang")
        def call_critic(prompt):
            r = llm_client.chat(prompt)
            return {"response": r.text, "model": r.model,
                    "tokens_in": r.usage.input, "tokens_out": r.usage.output}
    """

    def deco(f: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            r = Recorder(path=path, parser=parser)
            t0 = time.monotonic()
            result = f(*args, **kwargs)
            latency = time.monotonic() - t0

            if extract is not None:
                payload = extract(result)
            elif isinstance(result, dict):
                payload = result
            elif isinstance(result, str):
                payload = {"response": result}
            else:
                payload = {}

            if payload:
                r.observe(
                    response=payload.get("response", ""),
                    model=payload.get("model", ""),
                    tokens_in=payload.get("tokens_in", 0),
                    tokens_out=payload.get("tokens_out", 0),
                    latency_s=payload.get("latency_s", latency),
                    tags=payload.get("tags"),
                )
            return result

        return wrapper

    if fn is not None:
        return deco(fn)
    return deco
