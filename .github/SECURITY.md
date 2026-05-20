# Security Policy

## Scope

This project ships a parser, a spec, and a `sanitize()` function used to redact MLLANG packets before optional telemetry. The security surface this policy covers:

- **IP-leak bugs in `sanitize()`** — the function returns a payload that still contains user data the spec says should be redacted.
- **IP-leak bugs in any published MLLANG corpus** — anyone can audit a public Hugging Face dump and find a record that contains identifying user content.
- **Parser-side denial of service** — malformed packets that crash or hang the reference parser.
- **Spec-side ambiguity** that lets two compliant implementations disagree on slot semantics in a way that produces unsafe behavior.

The project does **not** currently operate a hosted telemetry endpoint, so there is no live API surface to attack today. When one exists, this policy will be updated to cover it.

## Reporting a vulnerability

Please use **GitHub's private vulnerability reporting** for this repository:

1. Go to the [Security tab](https://github.com/jakeliu/mllang/security/advisories).
2. Click **Report a vulnerability**.
3. Describe what you found, the impact, and a minimum reproducing input.

If GitHub private reporting is unavailable to you, open a non-public channel (e.g. emailing the maintainer listed in the repo profile) before filing a public issue.

**Please do not** open a regular public issue or PR with a working exploit. Wait for an acknowledgement first.

## What to expect

- Acknowledgement within **72 hours**.
- Triage and a planned-fix date within **7 days**.
- A coordinated disclosure window — typically 30 days for parser/library issues, longer if a published corpus has to be rotated.

## IP-leak bug bounty

We treat **published-corpus IP leaks** as the most serious class of bug because they cannot be reversed once dumps are mirrored.

If you find a verified IP leak in MLLANG-produced telemetry or a published MLLANG corpus, you may be eligible for a token bounty. This is **not** an industry-leading payout — it exists to lower the friction for disclosure, not to fund careers:

| Class | Bounty |
|-------|--------|
| Spec ambiguity that allows compliant leak | thanks + credit in release notes |
| `sanitize()` bug that produces a leaked payload at any documented level | $100 |
| Live published-corpus record containing email, file path, API key, or quoted user content | $100 per distinct leak class, capped at $500 per report |

Payments are at the maintainer's discretion. To qualify:

- The leak must violate the documented redaction rules in [`docs/telemetry.md`](../docs/telemetry.md).
- The report must include a minimum reproducing case (input packet + sanitize call or corpus record id).
- You must allow the coordinated disclosure window to elapse before going public.

Out of scope:
- Issues that require a user to manually set `reject_leaks=False` and then deliberately feed PII.
- Theoretical leaks with no reproducing input.
- Performance / DoS where the same payload is comparable to existing parser behavior.

## What we will not do

- We will not pursue legal action against good-faith researchers who follow this policy.
- We will not silently fix and re-publish without crediting the reporter (unless requested).
- We will not reveal reporter identity without consent.

---

Apache 2.0 license applies. This policy can change as the threat model evolves.
