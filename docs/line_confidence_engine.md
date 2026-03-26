# Line-Confidence Engine

This commit extracts DSAT's line-confidence logic into an explicit trust engine.

That matters because the repo's first subsystem slice is not “find Earth by magic.”
It is a bounded answer to a narrower question:

**How much trust should the system keep in its current communication-adjacent
state estimate, given what it is observing right now?**

## What the Engine Considers

The current engine consumes:

- baseline confidence
- pointing error
- telemetry freshness
- clock bias
- communication-window state
- resolved packet-loss pressure
- resolved sensor-bias pressure
- resolved mode-mismatch pressure
- resolved dropout pressure

## What the Engine Produces

For each assessment it returns:

- bounded confidence in `[0.0, 1.0]`
- a confidence status
- explicit penalty breakdown
- dominant degrading factors

## Why This Matters

Aerospace engineers should be able to inspect trust logic and ask:

- what reduced confidence?
- by how much?
- which factors dominated?
- when did the posture move from nominal to monitor, degraded, or critical?

This module exists so those questions have direct answers.

## Current Confidence Status Bands

The current status ladder is:

- `nominal`
- `monitor`
- `degraded`
- `critical`

These are bounded trust labels, not claims of final diagnosis.

## Current Penalty Model

The model is intentionally simple and explicit.

It applies capped penalties for:

- pointing error
- telemetry freshness
- clock bias
- packet loss
- sensor bias
- mode mismatch
- dropout
- closed communication window

The caps prevent one factor from dominating without bound.

## Design Posture

This is not a high-fidelity comms or orbital geometry model.
It is a deterministic trust model for a simulation-first assurance scaffold.

That is the correct level of claim for this repo.

## Integration in This Commit

The replay harness now:

- routes confidence computation through the line-confidence engine
- emits `line_confidence_assessed` events
- stores confidence status and dominant degrading factors in replay samples
- carries the final confidence posture in replay final state
