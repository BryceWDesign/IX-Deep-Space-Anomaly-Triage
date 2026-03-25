# Deterministic Replay Harness

This commit adds the first executable replay surface for DSAT.

The replay harness is intentionally narrow. It is **not yet** the anomaly
triage engine. It exists so that later logic can be judged against a stable,
repeatable execution path.

## What the Harness Does

For a validated scenario, the harness:

1. advances a fixed timeline at `tick_hz`
2. applies seeded-fault effects with explicit bounded math
3. updates communication-adjacent state
4. computes a line-confidence trace
5. emits a compact event stream
6. records deterministic samples

## Why This Matters

Without a replay harness, later triage claims are too easy to hand-wave.

With a replay harness, the repository can already answer:

- was the run repeatable?
- when did the anomaly threshold trip?
- what fault set was active at that moment?
- how did line confidence decay?
- what event sequence was emitted?

That gives later commits a hard surface to test against.

## Current Modeled State

The harness currently models:

- `line_confidence`
- `telemetry_freshness_s`
- `pointing_error_deg`
- `clock_bias_ms`
- `comm_window_open`
- `link_mode`

The model is deliberately simple and bounded.

## Current Fault Effects

This commit supports deterministic effects for:

- `pointing_drift`
- `packet_loss`
- `sensor_stale`
- `clock_bias_growth`
- `sensor_bias`
- `dropout`
- `mode_mismatch`

These are not intended to be high-fidelity physics models.
They are bounded replay drivers used to create measurable scenario behavior.

## Event Emission in This Commit

The replay harness may emit:

- `scenario_started`
- `anomaly_detected`
- `triage_emitted`
- `confidence_degraded`
- `recovery_action_bounded`

The later triage and safe-action commits will make these richer and more
policy-driven. Right now they are deterministic replay markers.

## CLI Usage

Validate a scenario:

```bash
ix-dsat --validate-scenario scenarios/examples/link_state_pointing_drift.json

Replay a scenario:

ix-dsat --replay-scenario scenarios/examples/link_state_pointing_drift.json

Replay a scenario while keeping every tenth tick as a sample:

ix-dsat --replay-scenario scenarios/examples/link_state_pointing_drift.json --sample-every 10
