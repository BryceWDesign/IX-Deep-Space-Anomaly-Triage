# Health Sentinel

This commit adds the first deterministic health sentinel for DSAT.

The health sentinel is intentionally narrower than full anomaly triage. Its job
is to inspect replay traces and produce bounded health findings that later
logic can build upon.

## What the Sentinel Does

For a replay result, the sentinel:

1. inspects bounded replay samples
2. checks explicit trust thresholds
3. emits deterministic findings
4. assigns an overall operating posture
5. recommends a bounded next posture

## What the Sentinel Does Not Do

It does **not** claim root-cause certainty.
It does **not** replace subsystem-specific diagnostics.
It does **not** make broad autonomy claims.

## Current Finding Categories

The sentinel currently checks:

- `line_confidence`
- `telemetry_freshness`
- `pointing_error`
- `clock_bias`
- `comm_window`
- `multi_fault_pressure`

These are first-pass health indicators, not final diagnosis.

## Current Status Ladder

The sentinel uses four bounded statuses:

- `nominal`
- `monitor`
- `degraded`
- `critical`

The overall report takes the highest status across all emitted findings.

## Recommended Postures

The sentinel currently maps overall status to one of four postures:

- `continue_nominal_ops`
- `continue_with_watchstanding`
- `bound_recovery_and_reduce_risk`
- `enter_bounded_recovery_only`

This is still not the safe-action gate. It is a precursor signal that later
commits will formalize.

## Why This Matters

Aerospace engineers do not need a vague “AI thinks something is wrong.”

They need a bounded answer to:

- what trust boundary got crossed?
- when did it happen?
- how severe is it?
- what operating posture should tighten next?

That is the purpose of this module.

## CLI Usage

Run a health-sentinel scan over a scenario:

```bash
ix-dsat --sentinel-scan scenarios/examples/link_state_pointing_drift.json --sample-every 10

