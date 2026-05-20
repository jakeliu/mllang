"""MLLANG operator definitions."""

# 19 operators (full set from v0.1 spec section 3)
OPERATORS = {
    "=": "is / equals",
    ":=": "assign",
    "==": "confirmed equal (verified)",
    "?": "unknown / open",
    "!": "assertion / must",
    "*": "important / pinned",
    "~": "approximate / loose",
    "^": "parent / prior round (e.g. ^r1)",
    "->": "leads to / next step",
    "=>": "implies / therefore",
    "<=>": "agreed by all parties (halt value)",
    "&": "and",
    "|": "or",
    "^!": "reserved compound (never appears bare)",
    "#": "tag / topic",
    "$": "tool-invocation shorthand (inside Y: slot only)",
    "[]": "list / set",
    "{}": "map / struct",
    "()": "group",
    ";": "slot separator",
    ",": "item separator",
}

# Agent codes
AGENT_CODES = {"@C", "@X", "@K", "@G", "@M", "@H", "@?"}
