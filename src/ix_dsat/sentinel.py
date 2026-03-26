from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable, Final

from ix_dsat.replay import ReplayResult, ReplaySample


STATUS_RANK: Final[dict[str, int]] = {
    "nominal": 0,
    "monitor": 1,
    "degraded": 2,
    "critical": 3,
}


@dataclass(frozen=True, slots=True)
class SentinelFinding:
    """
    One deterministic health-sentinel finding.
    """

    category: str
    status: str
    message: str
    time_s: float | None
    value: float | bool
    threshold: float | bool
    evidence: dict[str, float | bool | str]


@dataclass(frozen=True, slots=True)
class SentinelReport:
    """
    Health-sentinel report derived from a replay result.
    """

    scenario_id: str
    overall_status: str
    recommended_posture: str
    findings: tuple[SentinelFinding, ...]
    metrics: dict[str, float | bool | int | None]

    def to_dict(self) -> dict[str, object]:
        """
        Return a JSON-serializable report.
        """
        return {
            "scenario_id": self.scenario_id,
            "overall_status": self.overall_status,
            "recommended_posture": self.recommended_posture,
            "finding_count": len(self.findings),
            "findings": [asdict(finding) for finding in self.findings],
            "metrics": self.metrics,
        }

    def summary(self) -> dict[str, object]:
        """
        Return a compact summary suitable for CLI output.
        """
        return {
            "scenario_id": self.scenario_id,
            "overall_status": self.overall_status,
            "recommended_posture": self.recommended_posture,
            "finding_count": len(self.findings),
            "finding_categories": [finding.category for finding in self.findings],
            "metrics": self.metrics,
        }


def _max_status(left: str, right: str) -> str:
    return left if STATUS_RANK[left] >= STATUS_RANK[right] else right


def _recommended_posture(overall_status: str) -> str:
    mapping = {
        "nominal": "continue_nominal_ops",
        "monitor": "continue_with_watchstanding",
        "degraded": "bound_recovery_and_reduce_risk",
        "critical": "enter_bounded_recovery_only",
    }
    return mapping[overall_status]


def _first_sample_matching(
    samples: tuple[ReplaySample, ...],
    predicate: Callable[[ReplaySample], bool],
) -> ReplaySample | None:
    for sample in samples:
        if predicate(sample):
            return sample
    return None


def _max_sample(
    samples: tuple[ReplaySample, ...],
    selector: Callable[[ReplaySample], float],
) -> ReplaySample | None:
    if not samples:
        return None
    return max(samples, key=selector)


def _min_sample(
    samples: tuple[ReplaySample, ...],
    selector: Callable[[ReplaySample], float],
) -> ReplaySample | None:
    if not samples:
        return None
    return min(samples, key=selector)


def _line_confidence_finding(samples: tuple[ReplaySample, ...]) -> SentinelFinding | None:
    minimum_sample = _min_sample(samples, lambda sample: sample.line_confidence)
    if minimum_sample is None:
        return None

    value = minimum_sample.line_confidence
    if value <= 0.35:
        status = "critical"
        threshold = 0.35
    elif value <= 0.65:
        status = "degraded"
        threshold = 0.65
    elif value <= 0.85:
        status = "monitor"
        threshold = 0.85
    else:
        return None

    return SentinelFinding(
        category="line_confidence",
        status=status,
        message="Line confidence dropped below bounded trust thresholds.",
        time_s=minimum_sample.time_s,
        value=round(value, 6),
        threshold=threshold,
        evidence={
            "pointing_error_deg": round(minimum_sample.pointing_error_deg, 6),
            "telemetry_freshness_s": round(minimum_sample.telemetry_freshness_s, 6),
            "clock_bias_ms": round(minimum_sample.clock_bias_ms, 6),
        },
    )


def _telemetry_freshness_finding(samples: tuple[ReplaySample, ...]) -> SentinelFinding | None:
    maximum_sample = _max_sample(samples, lambda sample: sample.telemetry_freshness_s)
    if maximum_sample is None:
        return None

    value = maximum_sample.telemetry_freshness_s
    if value >= 30.0:
        status = "critical"
        threshold = 30.0
    elif value >= 12.0:
        status = "degraded"
        threshold = 12.0
    elif value >= 5.0:
        status = "monitor"
        threshold = 5.0
    else:
        return None

    trigger_sample = _first_sample_matching(
        samples, lambda sample: sample.telemetry_freshness_s >= threshold
    )
    return SentinelFinding(
        category="telemetry_freshness",
        status=status,
        message="Telemetry freshness exceeded bounded trust thresholds.",
        time_s=None if trigger_sample is None else trigger_sample.time_s,
        value=round(value, 6),
        threshold=threshold,
        evidence={
            "line_confidence": round(maximum_sample.line_confidence, 6),
            "pointing_error_deg": round(maximum_sample.pointing_error_deg, 6),
        },
    )


def _pointing_error_finding(samples: tuple[ReplaySample, ...]) -> SentinelFinding | None:
    maximum_sample = _max_sample(samples, lambda sample: sample.pointing_error_deg)
    if maximum_sample is None:
        return None

    value = maximum_sample.pointing_error_deg
    if value >= 5.0:
        status = "critical"
        threshold = 5.0
    elif value >= 2.0:
        status = "degraded"
        threshold = 2.0
    elif value >= 1.0:
        status = "monitor"
        threshold = 1.0
    else:
        return None

    trigger_sample = _first_sample_matching(samples, lambda sample: sample.pointing_error_deg >= threshold)
    return SentinelFinding(
        category="pointing_error",
        status=status,
        message="Pointing error exceeded bounded operating thresholds.",
        time_s=None if trigger_sample is None else trigger_sample.time_s,
        value=round(value, 6),
        threshold=threshold,
        evidence={
            "line_confidence": round(maximum_sample.line_confidence, 6),
            "telemetry_freshness_s": round(maximum_sample.telemetry_freshness_s, 6),
        },
    )


def _clock_bias_finding(samples: tuple[ReplaySample, ...]) -> SentinelFinding | None:
    maximum_sample = _max_sample(samples, lambda sample: sample.clock_bias_ms)
    if maximum_sample is None:
        return None

    value = maximum_sample.clock_bias_ms
    if value >= 250.0:
        status = "critical"
        threshold = 250.0
    elif value >= 80.0:
        status = "degraded"
        threshold = 80.0
    elif value >= 20.0:
        status = "monitor"
        threshold = 20.0
    else:
        return None

    trigger_sample = _first_sample_matching(samples, lambda sample: sample.clock_bias_ms >= threshold)
    return SentinelFinding(
        category="clock_bias",
        status=status,
        message="Clock bias exceeded bounded trust thresholds.",
        time_s=None if trigger_sample is None else trigger_sample.time_s,
        value=round(value, 6),
        threshold=threshold,
        evidence={
            "line_confidence": round(maximum_sample.line_confidence, 6),
            "telemetry_freshness_s": round(maximum_sample.telemetry_freshness_s, 6),
        },
    )


def _comm_window_finding(samples: tuple[ReplaySample, ...]) -> SentinelFinding | None:
    closed_samples = [sample for sample in samples if not sample.comm_window_open]
    if not closed_samples:
        return None

    closed_ratio = len(closed_samples) / len(samples)
    if closed_ratio >= 0.30:
        status = "critical"
        threshold = 0.30
    else:
        status = "degraded"
        threshold = 0.01

    first_closed = closed_samples[0]
    return SentinelFinding(
        category="comm_window",
        status=status,
        message="Communication window was not continuously available during replay.",
        time_s=first_closed.time_s,
        value=round(closed_ratio, 6),
        threshold=threshold,
        evidence={
            "closed_sample_count": float(len(closed_samples)),
            "total_sample_count": float(len(samples)),
        },
    )


def _multi_fault_pressure_finding(samples: tuple[ReplaySample, ...]) -> SentinelFinding | None:
    maximum_fault_sample = _max_sample(samples, lambda sample: float(len(sample.active_fault_ids)))
    if maximum_fault_sample is None:
        return None

    fault_count = len(maximum_fault_sample.active_fault_ids)
    if fault_count >= 3:
        status = "degraded"
        threshold = 3.0
    elif fault_count >= 2:
        status = "monitor"
        threshold = 2.0
    else:
        return None

    return SentinelFinding(
        category="multi_fault_pressure",
        status=status,
        message="Multiple active faults overlapped within the replay window.",
        time_s=maximum_fault_sample.time_s,
        value=float(fault_count),
        threshold=threshold,
        evidence={
            "active_fault_ids": ",".join(maximum_fault_sample.active_fault_ids),
        },
    )


def scan_replay(result: ReplayResult) -> SentinelReport:
    """
    Produce a deterministic health-sentinel report from a replay result.
    """
    samples = result.samples
    findings: list[SentinelFinding] = []

    for finding in (
        _line_confidence_finding(samples),
        _telemetry_freshness_finding(samples),
        _pointing_error_finding(samples),
        _clock_bias_finding(samples),
        _comm_window_finding(samples),
        _multi_fault_pressure_finding(samples),
    ):
        if finding is not None:
            findings.append(finding)

    overall_status = "nominal"
    for finding in findings:
        overall_status = _max_status(overall_status, finding.status)

    minimum_line_confidence = (
        None if not samples else round(min(sample.line_confidence for sample in samples), 6)
    )
    maximum_telemetry_freshness = (
        None if not samples else round(max(sample.telemetry_freshness_s for sample in samples), 6)
    )
    maximum_pointing_error = (
        None if not samples else round(max(sample.pointing_error_deg for sample in samples), 6)
    )
    maximum_clock_bias = (
        None if not samples else round(max(sample.clock_bias_ms for sample in samples), 6)
    )
    comm_window_closed_any = any(not sample.comm_window_open for sample in samples)
    maximum_active_fault_count = 0 if not samples else max(len(sample.active_fault_ids) for sample in samples)

    metrics: dict[str, float | bool | int | None] = {
        "minimum_line_confidence": minimum_line_confidence,
        "maximum_telemetry_freshness_s": maximum_telemetry_freshness,
        "maximum_pointing_error_deg": maximum_pointing_error,
        "maximum_clock_bias_ms": maximum_clock_bias,
        "comm_window_closed_any": comm_window_closed_any,
        "maximum_active_fault_count": maximum_active_fault_count,
        "anomaly_detected": result.anomaly_detected,
        "first_anomaly_time_s": result.first_anomaly_time_s,
    }

    return SentinelReport(
        scenario_id=result.scenario_id,
        overall_status=overall_status,
        recommended_posture=_recommended_posture(overall_status),
        findings=tuple(findings),
        metrics=metrics,
    )
