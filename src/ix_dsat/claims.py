from __future__ import annotations

from dataclasses import dataclass
from typing import Final


SYSTEM_NAME: Final[str] = "IX-Deep-Space-Anomaly-Triage"
SYSTEM_SHORT_NAME: Final[str] = "DSAT"


@dataclass(frozen=True, slots=True)
class ScopePosture:
    """
    Repository scope posture.

    Attributes:
        mission:
            Short statement of the subsystem's job.
        first_target:
            The first technical slice that the repository will model.
        outputs:
            What the subsystem is expected to provide.
        claims:
            Positive claims the repository is allowed to make.
        non_claims:
            Claims the repository must not make.
    """

    mission: str
    first_target: str
    outputs: tuple[str, ...]
    claims: tuple[str, ...]
    non_claims: tuple[str, ...]


SCOPE: Final[ScopePosture] = ScopePosture(
    mission=(
        "Provide onboard anomaly triage and mission-assurance support for "
        "delayed-ground deep-space operations."
    ),
    first_target=(
        "Communication and adjacent vehicle-state trust: link-state health, "
        "pointing/state consistency, telemetry freshness, and bounded recovery guidance."
    ),
    outputs=(
        "What changed",
        "Most likely cause class",
        "What is affected next",
        "Confidence estimate",
        "Safe action envelope",
    ),
    claims=(
        "Simulation-first scaffold for deterministic scenario replay.",
        "Explicit scope around anomaly triage and safe-action support.",
        "Designed to rank fault hypotheses under degraded or partial telemetry.",
        "Designed to preserve an auditable event trail for later ground review.",
        "Intended to gate risky recovery attempts when confidence is insufficient.",
    ),
    non_claims=(
        "Not a flight-qualified system.",
        "Not a certification package.",
        "Not a replacement for GN&C, comms, or full spacecraft FDIR.",
        "Not a claim of autonomous mission execution.",
        "Not a claim of guaranteed anomaly detection or fault isolation correctness.",
    ),
)
