from __future__ import annotations

from dataclasses import dataclass

from ix_dsat.faults import FaultEffectAggregate


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


@dataclass(frozen=True, slots=True)
class LineConfidenceInputs:
    """
    Inputs to the line-confidence engine.
    """

    baseline_confidence: float
    pointing_error_deg: float
    telemetry_freshness_s: float
    clock_bias_ms: float
    comm_window_open: bool
    packet_loss_ratio: float
    sensor_bias_level: float
    mode_mismatch_level: float
    dropout_level: float


@dataclass(frozen=True, slots=True)
class ConfidencePenaltyBreakdown:
    """
    Penalty contributions applied to the baseline confidence.
    """

    pointing_penalty: float
    freshness_penalty: float
    clock_penalty: float
    packet_penalty: float
    bias_penalty: float
    mismatch_penalty: float
    dropout_penalty: float
    closed_window_penalty: float

    @property
    def total_penalty(self) -> float:
        """
        Total penalty applied to baseline confidence.
        """
        return (
            self.pointing_penalty
            + self.freshness_penalty
            + self.clock_penalty
            + self.packet_penalty
            + self.bias_penalty
            + self.mismatch_penalty
            + self.dropout_penalty
            + self.closed_window_penalty
        )

    def to_dict(self) -> dict[str, float]:
        """
        JSON-serializable penalty representation.
        """
        return {
            "pointing_penalty": round(self.pointing_penalty, 6),
            "freshness_penalty": round(self.freshness_penalty, 6),
            "clock_penalty": round(self.clock_penalty, 6),
            "packet_penalty": round(self.packet_penalty, 6),
            "bias_penalty": round(self.bias_penalty, 6),
            "mismatch_penalty": round(self.mismatch_penalty, 6),
            "dropout_penalty": round(self.dropout_penalty, 6),
            "closed_window_penalty": round(self.closed_window_penalty, 6),
            "total_penalty": round(self.total_penalty, 6),
        }


@dataclass(frozen=True, slots=True)
class ConfidenceAssessment:
    """
    Result of one line-confidence assessment.
    """

    confidence: float
    status: str
    penalties: ConfidencePenaltyBreakdown
    dominant_factors: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """
        JSON-serializable assessment representation.
        """
        return {
            "confidence": round(self.confidence, 6),
            "status": self.status,
            "penalties": self.penalties.to_dict(),
            "dominant_factors": list(self.dominant_factors),
        }


def build_inputs(
    *,
    baseline_confidence: float,
    pointing_error_deg: float,
    telemetry_freshness_s: float,
    clock_bias_ms: float,
    comm_window_open: bool,
    effects: FaultEffectAggregate,
) -> LineConfidenceInputs:
    """
    Construct line-confidence inputs from replay state and resolved fault effects.
    """
    return LineConfidenceInputs(
        baseline_confidence=baseline_confidence,
        pointing_error_deg=pointing_error_deg,
        telemetry_freshness_s=telemetry_freshness_s,
        clock_bias_ms=clock_bias_ms,
        comm_window_open=comm_window_open,
        packet_loss_ratio=effects.packet_loss_ratio,
        sensor_bias_level=effects.sensor_bias_level,
        mode_mismatch_level=effects.mode_mismatch_level,
        dropout_level=effects.dropout_level,
    )


def _compute_penalties(inputs: LineConfidenceInputs) -> ConfidencePenaltyBreakdown:
    pointing_penalty = min(0.72, max(0.0, inputs.pointing_error_deg - 0.25) * 0.18)
    freshness_penalty = min(0.18, max(0.0, inputs.telemetry_freshness_s - 0.75) * 0.012)
    clock_penalty = min(0.12, max(0.0, inputs.clock_bias_ms - 2.0) * 0.0006)
    packet_penalty = min(0.25, inputs.packet_loss_ratio * 0.6)
    bias_penalty = min(0.20, inputs.sensor_bias_level * 0.20)
    mismatch_penalty = min(0.18, inputs.mode_mismatch_level * 0.18)
    dropout_penalty = 0.45 if inputs.dropout_level > 0.0 else 0.0
    closed_window_penalty = 0.22 if not inputs.comm_window_open else 0.0

    return ConfidencePenaltyBreakdown(
        pointing_penalty=pointing_penalty,
        freshness_penalty=freshness_penalty,
        clock_penalty=clock_penalty,
        packet_penalty=packet_penalty,
        bias_penalty=bias_penalty,
        mismatch_penalty=mismatch_penalty,
        dropout_penalty=dropout_penalty,
        closed_window_penalty=closed_window_penalty,
    )


def _dominant_factors(penalties: ConfidencePenaltyBreakdown) -> tuple[str, ...]:
    labeled = {
        "pointing_error": penalties.pointing_penalty,
        "telemetry_freshness": penalties.freshness_penalty,
        "clock_bias": penalties.clock_penalty,
        "packet_loss": penalties.packet_penalty,
        "sensor_bias": penalties.bias_penalty,
        "mode_mismatch": penalties.mismatch_penalty,
        "dropout": penalties.dropout_penalty,
        "closed_comm_window": penalties.closed_window_penalty,
    }
    significant = [(name, value) for name, value in labeled.items() if value >= 0.05]
    significant.sort(key=lambda item: item[1], reverse=True)

    if not significant:
        return ("nominal_margin",)

    return tuple(name for name, _value in significant[:3])


def _status_from_confidence(confidence: float) -> str:
    if confidence <= 0.35:
        return "critical"
    if confidence <= 0.65:
        return "degraded"
    if confidence <= 0.85:
        return "monitor"
    return "nominal"


def assess_line_confidence(inputs: LineConfidenceInputs) -> ConfidenceAssessment:
    """
    Assess bounded trust in the current communication-adjacent state estimate.
    """
    penalties = _compute_penalties(inputs)
    confidence = _clamp(inputs.baseline_confidence - penalties.total_penalty, 0.0, 1.0)
    return ConfidenceAssessment(
        confidence=confidence,
        status=_status_from_confidence(confidence),
        penalties=penalties,
        dominant_factors=_dominant_factors(penalties),
    )
