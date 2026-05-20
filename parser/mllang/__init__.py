"""MLLANG v0.1 reference parser — pure stdlib.

Usage:
    from mllang import Packet, parse, compose, extract_from_markdown

    p = parse("V:0.1.r1; I:demo; G:{task=test}; S:{x=1}; N:@K -> classify; H:<=>; P:0.85;")
    print(p.next_agent)   # @K
    print(p.halt)         # <=>
    print(p.confidence)   # 0.85

    text = compose(p)
    packets = extract_from_markdown(open("task.md").read())
"""

from .packet import Packet, parse, compose, extract_from_markdown, validate
from .slots import SLOT_ORDER, REQUIRED_SLOTS
from .halt import HALT_ENUM
from .operators import OPERATORS
from .sanitize import sanitize, sanitize_to_json, VALID_LEVELS as TELEMETRY_LEVELS
from .embed import embed_in_markdown, extract_summary_and_packet

__version__ = "0.1.6"

__all__ = [
    "Packet",
    "parse",
    "compose",
    "extract_from_markdown",
    "validate",
    "sanitize",
    "sanitize_to_json",
    "TELEMETRY_LEVELS",
    "embed_in_markdown",
    "extract_summary_and_packet",
    "SLOT_ORDER",
    "REQUIRED_SLOTS",
    "HALT_ENUM",
    "OPERATORS",
    "__version__",
]
