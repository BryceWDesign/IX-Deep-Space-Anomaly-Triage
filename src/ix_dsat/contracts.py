from __future__ import annotations

from dataclasses import dataclass
from typing import Final


ALLOWED_CAUSE_CLASSES: Final[tuple[str, ...]] = (
    "link_state_degradation",
    "pointing_state_inconsistency",
    "timing_drift_or_stale_data",
    "sensor_disagreement_or_corruption",
    "recovery_attempt_risk_escalation",
)

ALLOWED_FAULT_TYPES: Final[tuple[str, ...]] = (
    "packet_loss",
    "pointing_drift",
    "clock_bias_growth",
    "sensor_stale",
    "sensor_bias",
    "dropout",
    "mode_mismatch",
)

ALLOWED_TELEMETRY_KINDS: Final[tuple[str, ...]] = (
    "scalar",
    "boolean",
    "enum",
)

ALLOWED_ACTIONS: Final[tuple[str, ...]] = (
    "hold_current_pointing",
    "request_reacquisition",
    "switch_to_low_rate_link",
    "freeze_high_risk_recovery",
    "shed_noncritical_traffic",
    "enter_safe_comm_posture",
    "await_fresh_state_estimate",
)

REQUIRED_EVENT_TYPES: Final[tuple[str, ...]] = (
    "scenario_started",
    "anomaly_detected",
    "triage_emitted",
)


@dataclass(frozen=True, slots=True)
class Bounds:
    """
    Simple numeric bounds contract.
    """

    minimum: float
    maximum: float


LINE_CONFIDENCE_BOUNDS: Final[Bounds] = Bounds(minimum=0.0, maximum=1.0)
TELEMETRY_FRESHNESS_BOUNDS: Final[Bounds] = Bounds(minimum=0.0, maximum=3600.0)
POINTING_ERROR_BOUNDS: Final[Bounds] = Bounds(minimum=0.0, maximum=180.0)
CLOCK_BIAS_BOUNDS: Final[Bounds] = Bounds(minimum=0.0, maximum=60_000.0)
SEVERITY_BOUNDS: Final[Bounds] = Bounds(minimum=0.0, maximum=1.0)
