"""MLLANG halt enum (9-way)."""

import re

# 9-way halt enum
HALT_ENUM = {
    "accept",
    "repair",
    "regen",
    "escalate@H",
    "test=pass",
    "test=fail",
    "risk!high",
    "<=>",
}

# after-N-rounds is a pattern, not a literal — handled separately
_AFTER_N_ROUNDS_RE = re.compile(r"^after-\d+-rounds$|^after-N-rounds$")


def is_valid_halt(halt_str: str) -> bool:
    """Check if a halt value (or pipe-separated multi-value) is valid."""
    if not halt_str:
        return False
    parts = [p.strip() for p in halt_str.split("|")]
    for part in parts:
        if part in HALT_ENUM:
            continue
        if _AFTER_N_ROUNDS_RE.match(part):
            continue
        return False
    return True


def halt_categories(halt_str: str) -> list:
    """Return list of halt categories in this halt string (after splitting by |)."""
    if not halt_str:
        return []
    return [p.strip() for p in halt_str.split("|")]
