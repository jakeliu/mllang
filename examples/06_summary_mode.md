# Migrate logs pipeline to OpenTelemetry

Workflow: cut Fluentd → OTel collector, dual-write 1 week, gate on backfill checksum match.

```mllang
V:0.1.r1; I:otel-migration-001;
G:{task=migrate_logging, from=fluentd, to=otel_collector, deadline=2026-07-01};
S:{prod_pipeline=fluentd, dual_write=on, backfill_window_d=7};
D:[dual_write_first, checksum_gate, rollback_kept_warm];
R:[backfill_drift, otel_collector_oom, downstream_alert_silence];
N:@K -> implement;
H:test=pass;
P:0.82;
EN: Cut Fluentd to OTel collector; dual-write 7d, checksum-gated cutover.
```

---

# Triage flaky test in CI

Workflow: bisect last 30 commits, reproduce locally with same seed, file or quarantine.

```mllang
V:0.1.r1; I:flaky-test-checkout-suite-014;
G:{task=triage_flake, scope=checkout_suite, parent=ci-stability-q3};
S:{failure_rate_pct=12, last_green_sha=a4f2c1, suspect_window_commits=30};
D:[git_bisect_with_seed_pin, reproduce_locally_3x, quarantine_if_unreproducible];
E:["ci_log:run_88421", "metrics_dashboard:flake_rate.png"];
U:[?root_cause_in_code_vs_infra];
R:[masking_real_regression_if_quarantined];
N:@C -> verify_root_cause;
H:test=pass | escalate@H;
P:0.65;
EN: Triage 12%-rate flake in checkout suite; bisect + repro before quarantine.
```

---

# Build LLM evaluation harness

Workflow: 5 axes × 3 model families × 200 prompts; gold-standard labels by 2 raters.

```mllang
V:0.1.r1; I:llm-eval-harness-v2;
G:{task=ship_eval_harness, axes=5, families=3, prompts_per_axis=200};
S:{harness_skeleton=ready, rater_agreement_target=0.85, dataset=internal_only};
D:[two_rater_kappa_gate, no_proprietary_prompts_logged, deterministic_seed];
E:["spec/eval_axes.md", "config/raters.yaml"];
U:[?budget_for_third_rater_if_disagreement];
R:[rater_drift_over_time, prompt_leakage_to_training_set];
T:{rater_kappa=fail};
N:@K -> implement;
H:test=pass;
P:0.78;
EN: Ship 5-axis × 3-family LLM eval harness; gate on 0.85 inter-rater kappa.
```

---

## How to read this file

Three independent tasks. Each is a one-line workflow summary plus a fenced `mllang` packet. Agents parse the packet and ignore the surrounding text. Humans skim the summary to know what's in the block before opening it.

The `EN:` line inside each packet is the dual-channel — a 1-sentence English summary baked into the structured payload itself, so even a tool that only sees the packet still has a human-readable digest.

No long prose duplicating the packet. Compact, agent-first.

## Load this file from Python

```python
from mllang import extract_from_markdown, extract_summary_and_packet

# All three packets
packets = extract_from_markdown(open("examples/06_summary_mode.md").read())
for p in packets:
    print(p.thread_id, p.next_agent, p.halt, p.confidence)

# Or first-block summary + packet
summary, packet = extract_summary_and_packet(open("examples/06_summary_mode.md").read())
print(summary)               # "Workflow: cut Fluentd → OTel collector, ..."
print(packet.next_agent)     # "@K -> implement"
```
