"""MLLANG slot definitions."""

# Canonical slot order (16 slots)
SLOT_ORDER = ["V", "I", "G", "S", "D", "E", "U", "R", "T", "F", "Y", "B", "N", "H", "P", "A"]

# Required slots (must be present for valid packet)
REQUIRED_SLOTS = ["V", "G", "S", "N", "H"]

# Slot meanings
SLOT_DESCRIPTIONS = {
    "V": "version + round (e.g. V:0.1.r1)",
    "I": "thread-id",
    "G": "goal-map {key=value, ...}",
    "S": "state-map {key=value, ...}",
    "D": "decisions [item, item, ...]",
    "E": "evidence [path, citation, ...]",
    "U": "unknowns [?question, ...]",
    "R": "risks [risk, ...]",
    "T": "test result {check=pass|fail, ...}",
    "F": "files [path, ...]",
    "Y": "tool-calls [$verb(args), ...]",
    "B": "budget cap {tokens=N, time=Ns, money=N}",
    "N": "next @agent -> verb",
    "H": "halt (see HALT_ENUM)",
    "P": "confidence float 0.00-1.00",
    "A": "assumptions [item, ...]",
}

# Slots that contain maps (key=value)
MAP_SLOTS = {"G", "S", "T", "B"}

# Slots that contain lists
LIST_SLOTS = {"D", "E", "U", "R", "F", "Y", "A"}

# Slots with scalar values
SCALAR_SLOTS = {"V", "I", "N", "H", "P"}
