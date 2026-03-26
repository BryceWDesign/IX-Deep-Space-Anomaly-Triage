# Seeded Fault Library

This commit extracts seeded fault behavior into a dedicated fault library.

That matters because DSAT should not hide replay-driving behavior inside one big
step function. Aerospace review gets easier when the fault models are explicit,
named, bounded, and testable on their own.

## What This Library Is

A deterministic catalog of replay-driving fault effects for the first DSAT
technical slice.

## What This Library Is Not

It is not a high-fidelity comms or spacecraft dynamics model.
It is not a substitute for subsystem-specific engineering analysis.
It is a bounded fault-effect layer for repeatable scenario execution.

## Design Rules

Each fault handler must be:

- deterministic
- bounded
- inspectable
- scenario-driven
- independent from later policy logic

## Current Fault Catalog

### `pointing_drift`

Models increasing pointing error over time.

Key derived quantity:

- `effective_drift_deg_per_s`

### `packet_loss`

Models downlink degradation without pretending to simulate the full channel.

Key derived quantity:

- `effective_loss_ratio`

### `sensor_stale`

Models update-age growth when a sensing source stops providing fresh truth.

Key derived quantity:

- `effective_age_growth_s_per_s`

### `clock_bias_growth`

Models growing timing disagreement.

Key derived quantity:

- `effective_bias_growth_ms_per_s`

### `sensor_bias`

Models disagreement or corruption pressure without hardcoding sensor-specific
physics.

Key derived quantity:

- `effective_bias_level`

### `dropout`

Models a severe communication interruption.

Key derived quantity:

- `effective_dropout_level`

### `mode_mismatch`

Models unsafe disagreement between expected and observed operating posture.

Key derived quantities:

- `effective_mismatch_score`
- `expected_mode`
- `observed_mode`

## Why This Matters for DSAT

The fault library is the bridge between static scenario contracts and later
health/triage reasoning.

It lets the repo answer:

- which seeded faults were active at a given time?
- what deterministic effects did they resolve into?
- what bounded observations were available for later triage?

## Review Posture

A future reviewer should be able to inspect a fault handler and say:

- what parameters drive it?
- what bounds cap it?
- what replay variables does it influence?
- what deterministic observation does it emit?

If that is not obvious, the fault model is too vague for this repo.
