# MLLANG v0.1 — 5-line summary

- **16 slots** in canonical order: `V I G S D E U R T F Y B N H P A`. Required slots: `V G S N H`.
- **19 operators**: `= := == ? ! * ~ ^ -> => <=> & | ^! # $ [ ] { } ( ) ; ,` (`$` valid only inside `Y:` tool-call slot; `^!` is a reserved compound).
- **9-way halt enum** for the `H:` slot: `accept | repair | regen | escalate@H | after-N-rounds | test=pass | test=fail | risk!high | <=>`.
- **Dual-channel rule**: every packet pairs with an `EN:` line ≤ 1 sentence. The packet is the structured payload; the `EN:` line is the human-skim channel.
- **ASCII only outside quoted strings.** Non-ASCII allowed only inside `"..."` quoted slot values.

Full spec: https://github.com/jakeliu/mllang/blob/main/spec/MLLANG_v0.1.locked.md
