# Safe-Action Gate

This commit adds DSAT's first explicit safe-action gate.

The gate is where the repo stops saying only “what is most plausible?” and
starts saying “what is still allowed right now?”

That matters because the savage pain point is not just detection. It is making
sure bad recovery choices are bounded when trust collapses.

## What the Gate Does

Given a scenario, replay result, sentinel report, and triage report, the gate:

1. computes an allow/deny action set
2. activates latch conditions when trust crosses critical boundaries
3. forces bounded-recovery-only posture when latches are active
4. records release conditions for each active latch
5. emits a compact operator summary

## What the Gate Does Not Do

It does **not** claim command authority over a real vehicle.
It does **not** replace certified flight-software interlocks.
It does **not** solve the full mission-operations problem.

It is a deterministic policy layer inside a simulation-first assurance scaffold.

## Current Inputs

The gate currently uses:

- the scenario action envelope
- replay evidence
- health-sentinel posture
- bounded triage posture

## Current Latches

The current gate can latch on:

- critical line confidence
- critical telemetry freshness
- critical clock bias
- communication-window loss
- overlapping multi-fault pressure

A latched gate enters bounded recovery only.

## What “Latched” Means Here

When latched, the gate tightens to a cause-class-specific safe core and blocks
everything else.

That is deliberate. A system with collapsing trust should not keep expanding
its action freedom.

## Output Surface

The gate currently emits:

- `latch_state`
- `active_latches`
- `allowed_actions`
- `blocked_actions`
- `gate_rationale`
- `operator_summary`

## Why This Matters

Aerospace engineers care about bounded authority.

The useful question is not:
“Did the AI say something scary?”

The useful question is:
“When confidence falls apart, what exactly is the system still allowed to do?”

That is what this module starts answering.

## CLI Usage

Run the full gate scan over a scenario:

```bash
ix-dsat --gate-scan scenarios/examples/link_state_pointing_drift.json --sample-every 10
