# Assurance Posture

## What This Repository Is

A narrow subsystem scaffold for onboard anomaly triage and safe-action support
when ground response is delayed.

## What This Repository Is Not

It is not a marketing vehicle for broad autonomy claims.
It is not a surrogate for formal certification.
It is not a replacement for domain subsystems such as GN&C, communications,
power management, or full mission planning.

## Claims Allowed in This Repository

The repository may claim only what the code and artifacts can support:

- deterministic replay exists
- fault scenarios are explicitly modeled
- confidence values are computed by defined logic
- action gates are traceable to policy rules
- event evidence is retained for later review

## Claims Not Allowed in This Repository

The repository must not claim:

- flight qualification
- operational readiness for crewed missions
- guaranteed anomaly detection performance
- guaranteed fault isolation correctness
- replacement of certified avionics or mission operations
- broad AI autonomy capability

## Review Standard

Each future capability must be traceable to:

1. a defined input contract
2. a deterministic or bounded algorithmic path
3. an output contract
4. scenario-based evidence
5. explicit limitations
