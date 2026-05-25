# MLLANG Protocol Maturity Log

Tracks MLLANG protocol coverage over time. Update each session that materially shifts a number. Keep brutal — overstating wastes future effort.

## Scoring rubric

- **0–30%**: stub / placeholder / one vendor / no tests
- **30–60%**: working core, narrow surface, gaps in vendor support or test coverage
- **60–80%**: broad surface, tested, missing polish / extra vendors / docs
- **80–95%**: production-ready except known minor items
- **95–100%**: locked, ratified, externally validated

## Snapshots

### 2026-05-19 — v0.1 LOCK
v0.1 spec frozen across 8 deployments / 5 vendor families. Mean ratification 0.95.

### 2026-05-24 — v0.2 LOCK

| Item | % | Evidence | Gap |
|---|---|---|---|
| Slot grammar | 100 | v0.1 immutable; v0.2 strict superset adds T:cap / CAP: / TR: / SIG: / map-form N: | none |
| Cross-vendor compose+parse | 95 | Anthropic ✓ · OpenAI Codex ✓ · Google Gemini ✓ (map-form N: required) · Open-weight Gemma ✓ (two sizes) | Chinese-vendor family not yet tested; no independent third-party use |
| Conformance suite | 100 | 180/180 (166 v0.1 + 14 v0.2) | — |
| RFC + ratification | 100 | RFC 0001 ratified 4 approve / 0 reject; voting packets archived | one jury seat left blank (informational) |
| Spec doc | 100 | `MLLANG_v0.2.locked.md` written and locked | — |
| PyPI release | pending | Parser version bumped to 0.2.0; CHANGELOG entry written | `git tag v0.2.0 && git push origin v0.2.0` not yet executed |

**Overall:** 95% — v0.2 LOCKED. Reaching 100% needs PyPI publication + at least one third-party (not the maintainers) using the protocol.

---

## Improvement priorities

1. `git tag v0.2.0 && git push` → PyPI publishes `mllang-protocol==0.2.0`
2. Chinese-vendor inter-op test (DeepSeek / Qwen / GLM / Yi / Kimi) — quote+round-trip via packet
3. Independent third-party adoption signal (someone else publishes a parser or harness)
4. Begin v0.3 RFC window — candidates: P: banding inline with float, compression-tier slot, T:route packet type

---

## Template for next snapshot

```
### YYYY-MM-DD

| Item | % | Evidence | Gap |
|---|---|---|---|
| ... | _ | _ | _ |

**Notable shifts:** _
```
