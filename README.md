# IX-Deep-Space-Anomaly-Triage

Simulation-first onboard anomaly triage and mission-assurance scaffold for delayed-ground deep-space operations.

## One-line purpose

IX-Deep-Space-Anomaly-Triage (DSAT) is a narrow subsystem scaffold for deciding, under degraded or partial telemetry, **what changed, what is most likely wrong, what is affected next, how confident the system is, and what bounded action remains safe** when ground cannot respond in time.

## Why this repo exists

Delayed-ground operations create a brutal systems problem: when communication quality, state trust, timing alignment, or sensing integrity begin to degrade, a vehicle or crew cannot depend on rapid ground intervention to untangle the situation.

This repository does **not** claim to solve deep-space autonomy as a whole.

It does something narrower and more defensible:

1. validates deterministic seeded-fault scenarios
2. replays them repeatably
3. computes bounded trust in the current communication-adjacent line state
4. emits first-pass health findings
5. ranks plausible cause classes
6. gates actions into bounded recovery when trust collapses
7. preserves a blackbox-style evidence chain
8. packages that evidence for later store-and-forward sync
9. measures the run against explicit validation checks

That is the correct scope for a simulation-first aerospace-facing repo.

## Core framing

DSAT is an **onboard anomaly-triage and mission-assurance subsystem**.

It is **not**:

- a flight-qualified system
- a certification package
- a replacement for GN&C
- a replacement for communications hardware/software
- a replacement for full spacecraft FDIR
- a claim of autonomous mission execution
- a claim of guaranteed diagnosis correctness

## First technical slice

The first repository version focuses on:

- communication-adjacent anomaly triage
- line-confidence and link-state trust
- pointing/state consistency
- telemetry freshness and data staleness
- timing bias pressure
- bounded recovery posture under uncertainty

That means the current repo lives in the space between raw telemetry ingestion and high-consequence mission decision-making.

## The five operator questions

The current DSAT chain is built to help answer five questions:

1. What changed?
2. What is the most likely cause class?
3. What else is affected next?
4. How sure is the system?
5. What action remains safe right now?

## Current architecture

The current repository contains the following bounded subsystem layers.

### 1. Scenario contracts

Deterministic scenario JSON contracts define:

- metadata
- timeline
- initial state
- telemetry channels
- seeded faults
- expected cause class
- expected confidence floor
- expected action envelope
- required replay events

This forces scenario construction to stay explicit and reviewable.

### 2. Replay harness

The replay harness:

- steps time deterministically
- applies seeded faults
- updates bounded state variables
- emits replay events
- records replay samples

This creates a stable surface for later health, triage, and gate logic.

### 3. Seeded fault library

The fault library converts active faults into deterministic effect aggregates and observations.

Current modeled fault types:

- `pointing_drift`
- `packet_loss`
- `sensor_stale`
- `clock_bias_growth`
- `sensor_bias`
- `dropout`
- `mode_mismatch`

These are replay drivers, not claims of high-fidelity subsystem physics.

### 4. Line-confidence engine

The line-confidence engine makes DSAT's trust posture explicit.

It assesses bounded confidence from:

- pointing error
- telemetry freshness
- clock bias
- communication-window state
- packet-loss pressure
- sensor-bias pressure
- mode-mismatch pressure
- dropout pressure

It emits:

- confidence value in `[0.0, 1.0]`
- confidence status
- penalty breakdown
- dominant degrading factors

### 5. Health sentinel

The health sentinel converts replay traces into deterministic health findings.

Current finding categories:

- `line_confidence`
- `telemetry_freshness`
- `pointing_error`
- `clock_bias`
- `comm_window`
- `multi_fault_pressure`

It emits an overall posture of:

- `nominal`
- `monitor`
- `degraded`
- `critical`

### 6. Anomaly triage engine

The triage engine turns replay evidence and health findings into a ranked hypothesis set.

Current cause classes:

- `link_state_degradation`
- `pointing_state_inconsistency`
- `timing_drift_or_stale_data`
- `sensor_disagreement_or_corruption`
- `recovery_attempt_risk_escalation`

For each run it emits:

- ranked hypotheses
- supporting evidence categories
- affected surfaces
- preliminary recommended actions
- preliminary blocked actions
- operator summary

### 7. Safe-action gate

The gate turns bounded posture into explicit action allow/deny behavior.

It supports latch conditions for:

- critical line confidence
- critical telemetry freshness
- critical clock bias
- communication-window loss
- overlapping multi-fault pressure

When latched, the gate forces bounded recovery only.

### 8. Blackbox evidence ledger

The ledger is append-only and chain-hashed.

It records:

- scenario contract snapshot
- replay summary
- replay events
- sentinel report
- triage report
- gate report

The purpose is to preserve what DSAT believed, when it believed it, and what it allowed or blocked.

### 9. Delay-tolerant sync queue

The sync queue packages evidence ledger records into deterministic store-and-forward envelopes with:

- bounded envelope sizing
- priority ordering
- manifest hashing
- deterministic packaging order

This is not real networking. It is a deterministic export model for delayed contact opportunities.

### 10. Metrics and validation

The repo computes bounded metrics and explicit pass/fail checks so the system can be judged by measurable behavior rather than architecture theater.

Current validation covers:

- anomaly detection
- primary cause match
- replay cause hint match
- required event coverage
- confidence floor crossing
- gate latching under critical trust loss
- bounded-recovery core presence
- positive hypothesis separation
- evidence ledger population
- critical-first sync priority

## Current modeled state

The replay chain currently tracks:

- `line_confidence`
- `telemetry_freshness_s`
- `pointing_error_deg`
- `clock_bias_ms`
- `comm_window_open`
- `vehicle_mode`
- `link_mode`

## Repository layout

```text
.
├── LICENSE
├── pyproject.toml
├── docs/
│   ├── anomaly_triage_engine.md
│   ├── assurance_posture.md
│   ├── blackbox_evidence_and_sync.md
│   ├── data_contracts.md
│   ├── fault_library.md
│   ├── health_sentinel.md
│   ├── line_confidence_engine.md
│   ├── mission_scope.md
│   ├── replay_harness.md
│   ├── safe_action_gate.md
│   ├── system_context.md
│   └── validation_metrics.md
├── schemas/
│   └── scenario.schema.json
├── scenarios/
│   └── examples/
│       ├── link_state_pointing_drift.json
│       └── timing_bias_growth.json
├── src/
│   └── ix_dsat/
│       ├── __init__.py
│       ├── __main__.py
│       ├── claims.py
│       ├── cli.py
│       ├── contracts.py
│       ├── errors.py
│       ├── faults.py
│       ├── gate.py
│       ├── ledger.py
│       ├── line_confidence.py
│       ├── metrics.py
│       ├── replay.py
│       ├── scenario.py
│       ├── sentinel.py
│       ├── sync_queue.py
│       ├── triage.py
│       ├── validation.py
│       └── version.py
└── tests/
    ├── test_claims.py
    ├── test_cli.py
    ├── test_faults.py
    ├── test_gate.py
    ├── test_ledger.py
    ├── test_line_confidence.py
    ├── test_metrics.py
    ├── test_replay.py
    ├── test_scenario.py
    ├── test_sentinel.py
    ├── test_sync_queue.py
    ├── test_triage.py
    └── test_validation.py

Install

Create a virtual environment and install the package in editable mode.

python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]

On Windows PowerShell:
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
Run tests
pytest
CLI quickstart

Print repo scope posture:
ix-dsat --json

Print version:
ix-dsat --version

Validate a scenario contract:
ix-dsat --validate-scenario scenarios/examples/link_state_pointing_drift.json

Replay a deterministic scenario:
ix-dsat --replay-scenario scenarios/examples/link_state_pointing_drift.json --sample-every 10

Run the health sentinel:
ix-dsat --sentinel-scan scenarios/examples/link_state_pointing_drift.json --sample-every 10

Run bounded anomaly triage:
ix-dsat --triage-scan scenarios/examples/link_state_pointing_drift.json --sample-every 10

Run the safe-action gate:
ix-dsat --gate-scan scenarios/examples/link_state_pointing_drift.json --sample-every 10

Build the blackbox evidence ledger summary:
ix-dsat --ledger-scan scenarios/examples/link_state_pointing_drift.json --sample-every 10

Build the delay-tolerant sync queue summary:
ix-dsat --sync-queue-scan scenarios/examples/link_state_pointing_drift.json --sample-every 10

Compute end-to-end metrics:
ix-dsat --metrics-scan scenarios/examples/link_state_pointing_drift.json --sample-every 10

Run end-to-end validation:
ix-dsat --validate-run scenarios/examples/link_state_pointing_drift.json --sample-every 10
Example scenarios
link_state_pointing_drift.json

This scenario exercises:
increasing pointing drift
packet loss
stale star-tracker update pressure
link-state degradation
bounded recovery posture

Expected cause class:
link_state_degradation
timing_bias_growth.json

This scenario exercises:
clock-bias growth
stale-state pressure
timing-linked trust collapse
bounded recovery posture under stale timing truth

Expected cause class:
timing_drift_or_stale_data
What “line confidence” means here

The term line confidence in this repo is a bounded trust score in the current communication-adjacent state estimate.

It does not mean exact geometric truth.
It does not mean perfect Earth-direction knowledge.
It does not claim exact optical or RF pointing physics.

It means:
How much confidence should DSAT retain in its current line-of-state trust, given the observed pressure from pointing error, stale telemetry, timing drift, communication-window state, and resolved fault effects?

That is the right claim level for this repo.

What makes this repo serious
This repository is meant to read like engineering scaffolding, not sci-fi packaging.

It is scoped to measurable behavior:
deterministic replay
explicit scenario contracts
bounded fault models
explicit trust penalties
explicit sentinel thresholds
ranked cause hypotheses
explicit action allow/deny sets
chain-hashed evidence
deterministic sync packaging
pass/fail validation checks

A reviewer should be able to inspect the repo and answer:
what is the narrow subsystem claim?
what evidence is modeled?
what thresholds trigger posture changes?
what actions get blocked under critical trust loss?
what blackbox trail is preserved?
what did the seeded scenario actually prove?
Current limitations

These limitations are deliberate and should remain explicit.

DSAT currently does not provide:
orbital dynamics modeling
high-fidelity RF channel modeling
optical terminal modeling
real navigation or attitude estimation
real flight software integration
certification evidence
real delay-tolerant networking stack integration
spacecraft hardware interfaces
mission-specific procedures
ground-segment protocol implementation
Engineering posture

The intended review posture is:
narrow subsystem
deterministic behavior
bounded claims
auditable evidence
repeatable validation
zero magic language
Suggested review path

A technical reviewer can inspect the repo in this order:
docs/mission_scope.md
docs/system_context.md
docs/data_contracts.md
docs/replay_harness.md
docs/line_confidence_engine.md
docs/health_sentinel.md
docs/anomaly_triage_engine.md
docs/safe_action_gate.md
docs/blackbox_evidence_and_sync.md
docs/validation_metrics.md

Then run:
pytest
ix-dsat --validate-run scenarios/examples/link_state_pointing_drift.json --sample-every 10
ix-dsat --validate-run scenarios/examples/timing_bias_growth.json --sample-every 10
License

Apache License 2.0. See LICENSE.

Author
Bryce Lovell
