# IX-Deep-Space-Anomaly-Triage Mission Scope

## Purpose

IX-Deep-Space-Anomaly-Triage (DSAT) is a simulation-first onboard subsystem
scaffold for delayed-ground deep-space operations.

Its job is narrow:

1. Detect that trusted operating conditions may have changed.
2. Triage likely cause classes under degraded or partial telemetry.
3. Bound what recovery actions are still safe.
4. Preserve an auditable event trail for later ground review.

This repository does **not** claim to solve deep-space autonomy as a whole.

## First Technical Slice

The first target is:

- communication-adjacent anomaly triage
- link-state health
- pointing/state consistency
- telemetry freshness and data staleness
- bounded recovery guidance under uncertainty

This means the initial model is closer to a **mission-assurance and trust
subsystem** than to a flight controller.

## Core Operator Questions

The subsystem is expected to help answer five questions:

1. What changed?
2. What is the most likely cause class?
3. What else is affected next?
4. How sure is the system?
5. What action remains safe right now?

## In Scope

- deterministic scenario replay
- seeded fault injection
- explicit confidence handling
- fault-hypothesis ranking
- safe-action gating
- append-only event evidence
- delay-tolerant event summarization for later sync

## Out of Scope

- spacecraft guidance, navigation, and control
- replacing the communications subsystem
- replacing full spacecraft FDIR
- certification claims
- claims of flight readiness
- claims of guaranteed diagnosis correctness

## Engineering Posture

The repository is meant to be judged by measurable behavior:

- scenario coverage
- repeatability
- time to triage
- false-alarm behavior
- confidence decay under missing or corrupted data
- action-gate correctness
- evidence completeness
