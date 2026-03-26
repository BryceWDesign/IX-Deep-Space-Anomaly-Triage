# Validation Metrics and End-to-End Checks

This commit gives DSAT an explicit measurement and validation layer.

That matters because a serious aerospace-facing repo cannot stop at architecture.
It has to show what was measured, what passed, what failed, and why.

## Metrics Layer

The metrics layer computes bounded end-to-end quantities across the full DSAT
chain:

- anomaly-to-triage latency
- minimum line confidence
- expected confidence floor
- confidence margin to floor
- whether the floor was crossed
- primary cause match
- replay hint match
- hypothesis separation
- required-event coverage ratio
- gate latch count and latch state
- evidence-ledger record count
- sync-queue envelope count
- first sync priority

These metrics are intentionally reviewable and conservative.

## Validation Layer

The validation layer converts DSAT outputs into explicit checks, including:

- anomaly detected
- primary cause matches scenario expectation
- replay cause hint matches expectation
- required events are fully covered
- confidence floor is crossed for the seeded-fault scenario
- gate latches when trust crosses critical bounds
- bounded-recovery core actions are exposed
- hypothesis separation is positive
- ledger is populated
- sync queue prioritizes critical evidence first

## Why This Matters

A reviewer should be able to answer:

- did the scenario behave the way the contract said it should?
- did the triage result align with expectation?
- did the gate tighten correctly?
- did the blackbox and sync layers preserve the result?
- did the run pass a clear standard or not?

That is the point of this commit.

## CLI Usage

Compute metrics for a scenario:

```bash
ix-dsat --metrics-scan scenarios/examples/link_state_pointing_drift.json --sample-every 10

Run the full end-to-end validation:
ix-dsat --validate-run scenarios/examples/link_state_pointing_drift.json --sample-every 10

The outputs are compact JSON summaries. They are intended to support repeatable
engineering review, not presentation theater.
