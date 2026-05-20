# MLLANG RFC Voting Rules

---

## Quarterly windows

90-day review periods:

- Q1: Jan 1 — Mar 31
- Q2: Apr 1 — Jun 30
- Q3: Jul 1 — Sep 30
- Q4: Oct 1 — Dec 31

RFCs opened mid-window must wait until the next window's first month to enter voting.

---

## Eligibility

**Author:** anyone with a GitHub account.

**Voter:** anyone — but jury weight differs.

**Maintainers:** repo owners + co-maintainers (currently: @jakeliu).

---

## Jury composition (10 jury votes)

Family-balanced to prevent single-vendor capture:

- 2 votes from contributors whose primary usage is **Anthropic family** (Claude)
- 2 votes from contributors whose primary usage is **OpenAI family** (GPT / Codex)
- 2 votes from contributors whose primary usage is **Google family** (Gemini)
- 2 votes from contributors whose primary usage is **open-weight family** (Gemma / Llama / Qwen / DeepSeek / Mistral / etc.)
- 2 votes from spec maintainers

Plus unlimited community 👍 / 👎 (no jury weight, but counted as adoption signal).

### How jury voters are chosen

Year 1: jury = contributors who participated in v0.1 ratification + any volunteer who has merged ≥1 PR.

Year 2+: rotate 50% of jury each year, balanced by LLM family.

---

## Acceptance threshold

| Change scope | Required jury votes (out of 10) | Required community 👍 |
|--------------|---------------------------------|----------------------|
| Backward-compatible (new slot, new operator, new halt category) | ≥7 accept | ≥10 |
| Backward-incompatible (rename slot, remove operator, change required slot) | ≥9 accept | ≥20 |
| Editorial (typo, doc clarification) | maintainer fast-track, no vote needed | — |

Tie or below threshold = REJECTED. Author may revise and re-propose in next window.

---

## Multi-vendor test requirement

Every spec change RFC must include cross-vendor test results before voting opens:

- Minimum 3 LLM families tested
- Each must emit + parse roundtrip a packet using the proposed feature
- Failures noted in RFC, don't auto-reject — explain why a family fails

---

## Voting period

- Discussion: first 60 days of window
- Vote: last 30 days of window
- Author has 7-day rebuttal window after final vote before maintainer closes RFC

---

## Conflict resolution

If a vote is contested:

1. Author opens "appeal" issue within 7 days of decision
2. Maintainers re-read discussion thread
3. If process violation found, vote reopened next window
4. Otherwise decision stands

---

## Maintainer override

Maintainers (currently @jakeliu) can override jury vote ONLY for:
- Security issues
- Spec ambiguity that prevents implementation
- Backward-compatibility breakage missed in vote

Maintainer overrides logged in `rfc/MAINTAINER_OVERRIDES.md` for transparency.

---

## Version bump triggers

After RFC window closes:

- ≥1 RFC accepted → minor version bump (v0.x → v0.(x+1))
- ≥1 backward-incompatible RFC accepted → major version bump (v0.x → v1.0)
- 0 RFCs accepted → no version bump, next window opens

---

## Why family-balanced

MLLANG was ratified across 5+ vendor families. Standards captured by a single vendor become marketing tools. Family balance prevents that.

If voting drifts toward a single family > 60% representation in 2 consecutive windows, maintainers MUST recruit voters from underrepresented families before next window.

---

End of voting rules. Last updated: 2026-05-20.
