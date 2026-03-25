# System Context

## Problem Statement

In delayed-ground deep-space operations, the vehicle and crew cannot rely on
rapid ground intervention. When telemetry is partial, stale, inconsistent, or
degraded, raw alerts alone are not enough. The system needs onboard support
that can narrow the problem and avoid making the situation worse.

## DSAT's Place in the Stack

DSAT sits above raw telemetry ingestion and below high-consequence operational
decision-making.

It is intended to consume state summaries and produce bounded triage outputs:

- anomaly indication
- likely cause class
- confidence estimate
- immediate downstream impact hints
- safe action envelope
- event log entries

## Initial Cause Classes

The first repository version is expected to reason over high-level cause
classes rather than pretending to know precise root cause in all cases.

Examples include:

- link-state degradation
- pointing/state inconsistency
- timing drift or stale data
- sensor disagreement or corruption
- recovery attempt risk escalation

## Why the Narrow Scope Matters

Deep-space mission assurance is a systems problem, not a single algorithm.
Attempting to solve the whole stack in one repository would weaken credibility.

DSAT is deliberately narrow so that:

- scenarios can be deterministic
- evidence can be reproducible
- claims can be bounded
- later subsystem integration remains possible
