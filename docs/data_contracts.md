# Scenario Data Contracts

This document defines the deterministic scenario contract for the first DSAT
technical slice.

## Goal

Scenarios are meant to be:

- explicit
- bounded
- replayable
- reviewable by engineers
- strict enough to reject vague or inflated test inputs

The contract is intentionally narrow so later replay and triage behavior can be
measured cleanly.

## Root Fields

Each scenario JSON file must contain:

- `schema_version`
- `scenario_id`
- `title`
- `description`
- `metadata`
- `timeline`
- `initial_state`
- `telemetry_channels`
- `faults`
- `expected`

`schema_version` is currently fixed at `1.0.0`.

## Metadata

`metadata` fields:

- `domain` — free-text domain label such as `deep_space_operations`
- `subsystem` — first target subsystem slice
- `author` — scenario author
- `tags` — non-empty list of strings

## Timeline

`timeline` fields:

- `duration_s` — positive integer
- `tick_hz` — positive integer

This repository does not yet execute the replay loop, but the contract is
already fixed so future run behavior is deterministic and testable.

## Initial State

`initial_state` fields:

- `comm_window_open` — boolean
- `line_confidence` — float in [0.0, 1.0]
- `vehicle_mode` — non-empty string
- `telemetry_freshness_s` — float in [0.0, 3600.0]
- `pointing_error_deg` — float in [0.0, 180.0]
- `clock_bias_ms` — float in [0.0, 60000.0]

## Telemetry Channels

`telemetry_channels` is a non-empty list.

Each channel must define:

- `name`
- `kind` — one of `scalar`, `boolean`, `enum`
- `units`
- `nominal_min`
- `nominal_max`
- `initial_value`

Rules:

- channel names must be unique
- `nominal_min <= nominal_max`
- scalar initial values must fall within nominal bounds

## Faults

`faults` is a list of seeded faults.

Each fault must define:

- `fault_id`
- `fault_type`
- `start_s`
- `end_s` — optional
- `target`
- `severity`
- `parameters`

Allowed `fault_type` values in this repo version:

- `packet_loss`
- `pointing_drift`
- `clock_bias_growth`
- `sensor_stale`
- `sensor_bias`
- `dropout`
- `mode_mismatch`

Rules:

- fault IDs must be unique
- `severity` must be within [0.0, 1.0]
- times must remain inside scenario duration
- `end_s`, when provided, must be >= `start_s`

## Expected Behavior

`expected` defines what a later replay or triage run should preserve.

Fields:

- `cause_class`
- `minimum_confidence_floor`
- `allowed_actions`
- `blocked_actions`
- `must_emit_events`

Allowed `cause_class` values:

- `link_state_degradation`
- `pointing_state_inconsistency`
- `timing_drift_or_stale_data`
- `sensor_disagreement_or_corruption`
- `recovery_attempt_risk_escalation`

Allowed actions:

- `hold_current_pointing`
- `request_reacquisition`
- `switch_to_low_rate_link`
- `freeze_high_risk_recovery`
- `shed_noncritical_traffic`
- `enter_safe_comm_posture`
- `await_fresh_state_estimate`

Required events:

- `scenario_started`
- `anomaly_detected`
- `triage_emitted`

Rules:

- allowed and blocked action sets must be disjoint
- required events must be present in `must_emit_events`
- confidence floor must be within [0.0, 1.0]

## Design Intent

This contract exists to make future behavior measurable.

It does **not** imply that root-cause truth is always knowable.
It does **not** claim that diagnosis will always be correct.
It exists to force deterministic, reviewable, bounded scenario construction.
