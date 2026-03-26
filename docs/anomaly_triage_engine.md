# Anomaly Triage Engine

This commit adds DSAT's first bounded anomaly-triage engine.

The key phrase is **bounded**.

This engine does not pretend to know exact root cause with flight-grade truth.
It ranks plausible cause classes from replay evidence and health findings, then
gives operators a disciplined starting posture.

## What the Engine Does

Given a replay result and sentinel report, the triage engine:

1. ranks cause classes
2. retains rationale for each score contribution
3. identifies likely affected surfaces
4. recommends a preliminary bounded action posture
5. preserves ambiguity instead of hiding it

## Current Cause Classes

The engine currently ranks:

- `link_state_degradation`
- `pointing_state_inconsistency`
- `timing_drift_or_stale_data`
- `sensor_disagreement_or_corruption`
- `recovery_attempt_risk_escalation`

These are intentionally broad. At this stage, that is the correct engineering
posture for a simulation-first subsystem scaffold.

## Evidence Sources Used in This Commit

The engine currently scores hypotheses from:

- replay cause-class hint
- health-sentinel findings
- resolved fault types seen during replay
- dominant confidence-degradation factors
- overall replay posture

## Why This Matters

Without triage, the repo can say “something went wrong.”

With triage, the repo can say something more useful:

- what class of problem is most plausible?
- what other class is still meaningfully in play?
- which surfaces are likely affected next?
- what operator posture should tighten immediately?

That is a real step toward the savage pain point without pretending the whole
problem is solved.

## Preliminary Action Posture

This commit emits:

- `preliminary_recommended_actions`
- `preliminary_blocked_actions`

These are still **preliminary**. They are not yet the formal safe-action gate.
The next stage should convert this posture into an explicit allow/deny policy
layer with latching and bounded recovery transitions.

## Review Posture

A reviewer should be able to inspect a triage result and answer:

- why was this cause class ranked first?
- what evidence pushed its score?
- what ambiguity remains?
- what surfaces are likely affected?
- what immediate actions should be favored or avoided?

If the engine cannot answer those, it is too vague for DSAT.
