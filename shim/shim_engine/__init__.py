"""shim-engine — local-first observability for LLM-agent loops.

Wrap any LLM call, get token/latency/cost/outcome metrics into a JSONL
log. Zero hard dependencies; optional MLLANG awareness when installed
with the `[mllang]` extra.

Usage:
    from shim_engine import record

    with record("calls.jsonl") as r:
        response = llm_client.chat(...)
        r.observe(
            response=response.text,
            model="claude-opus",
            tokens_in=200,
            tokens_out=80,
            latency_s=2.1,
            tags={"call_type": "critic"},
        )

CLI:
    shim-engine-report calls.jsonl
"""

from .core import (
    DEFAULT_LOG_PATH,
    Recorder,
    instrument,
    observe,
    record,
)

__version__ = "0.1.0"

__all__ = [
    "Recorder",
    "record",
    "observe",
    "instrument",
    "DEFAULT_LOG_PATH",
    "__version__",
]
