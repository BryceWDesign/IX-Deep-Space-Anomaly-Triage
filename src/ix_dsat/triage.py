from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Final

from ix_dsat.replay import ReplayResult
from ix_dsat.sentinel import SentinelFinding, SentinelReport


CAUSE_CLASSES: Final[tuple[str, ...]] = (
    "link_state_degradation",
    "pointing_state_inconsistency",
    "timing_drift_or_stale_data",
    "sensor_disagreement_or_corruption",
    "recovery_attempt_risk_escalation",
)

CAUSE_TO_SURFACES: Final[dict[str, tuple[str, ...]]] = {
    "link_state_degradation": (
        "communications continuity",
        "state-estimate trust",
        "downlink posture",
    ),
    "pointing_state_inconsistency": (
        "line-of-sight maintenance",
        "attitude-linked trust",
        "reacquisition risk",
    ),
    "timing_drift_or_stale_data": (
        "temporal alignment",
        "telemetry freshness trust",
        "recovery timing",
    ),
    "sensor_disagreement_or_corruption": (
        "measurement trust",
        "cross-sensor agreement",
        "diagnostic confidence",
    ),
    "recovery_attempt_risk_escalation": (
        "operator action safety",
        "mode-transition trust",
        "bounded recovery posture",
    ),
}

PRELIMINARY_POLICY: Final[dict[str, dict[str, tuple[str, ...]]]] = {
    "link_state_degradation": {
        "recommended": (
            "switch_to_low_rate_link",
            "shed_noncritical_traffic",
            "request_reacquisition",
        ),
        "blocked": (
            "enter_safe_comm_posture",
            "hold_current_pointing",
        ),
        "critical_recommended": (
            "switch_to_low_rate_link",
            "freeze_high_risk_recovery",
            "enter_safe_comm_posture",
            "await_fresh_state_estimate",
        ),
        "critical_blocked": (
            "request_reacquisition",
            "hold_current_pointing",
        ),
    },
    "pointing_state_inconsistency": {
        "recommended": (
            "hold_current_pointing",
            "request_reacquisition",
            "await_fresh_state_estimate",
        ),
        "blocked": (
            "shed_noncritical_traffic",
            "enter_safe_comm_posture",
        ),
        "critical_recommended": (
            "hold_current_pointing",
            "freeze_high_risk_recovery",
            "await_fresh_state_estimate",
        ),
        "critical_blocked": (
            "request_reacquisition",
            "switch_to_low_rate_link",
        ),
    },
    "timing_drift_or_stale_data": {
        "recommended": (
            "await_fresh_state_estimate",
            "switch_to_low_rate_link",
            "freeze_high_risk_recovery",
        ),
        "blocked": (
            "request_reacquisition",
            "hold_current_pointing",
        ),
        "critical_recommended": (
            "await_fresh_state_estimate",
            "freeze_high_risk_recovery",
            "enter_safe_comm_posture",
        ),
        "critical_blocked": (
            "request_reacquisition",
            "hold_current_pointing",
            "shed_noncritical_traffic",
        ),
    },
    "sensor_disagreement_or_corruption": {
        "recommended": (
            "await_fresh_state_estimate",
            "freeze_high_risk_recovery",
            "shed_noncritical_traffic",
        ),
        "blocked": (
            "request_reacquisition",
            "hold_current_pointing",
        ),
        "critical_recommended": (
            "await_fresh_state_estimate",
            "freeze_high_risk_recovery",
            "enter_safe_comm_posture",
        ),
        "critical_blocked": (
            "request_reacquisition",
            "hold_current_pointing",
            "switch_to_low_rate_link",
        ),
    },
    "recovery_attempt_risk_escalation": {
        "recommended": (
            "freeze_high_risk_recovery",
            "await_fresh_state_estimate",
            "hold_current_pointing",
        ),
        "blocked": (
            "request_reacquisition",
            "enter_safe_comm_posture",
        ),
        "critical_recommended": (
            "freeze_high_risk_recovery",
            "await_fresh_state_estimate",
            "enter_safe_comm_posture",
        ),
        "critical_blocked": (
            "request_reacquisition",
            "hold_current_pointing",
            "switch_to_low_rate_link",
        ),
    },
}


@dataclass(frozen=True, slots=True)
class TriageHypothesis:
    """
    One ranked triage hypothesis.
    """

    cause_class: str
    score: float
    rationale: tuple[str, ...]
    supporting_categories: tuple[str, ...]
    affected_surfaces: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """
        JSON-serializable representation.
        """
        return {
            "cause_class": self.cause_class,
            "score": round(self.score, 6),
            "rationale": list(self.rationale),
            "supporting_categories": list(self.supporting_categories),
            "affected_surfaces": list(self.affected_surfaces),
        }


@dataclass(frozen=True, slots=True)
class TriageReport:
    """
    Full bounded triage report.
    """

    scenario_id: str
    overall_status: str
    primary_cause_class: str
    primary_confidence: float
    hypotheses: tuple[TriageHypothesis, ...]
    affected_surfaces: tuple[str, ...]
    preliminary_recommended_actions: tuple[str, ...]
    preliminary_blocked_actions: tuple[str, ...]
    operator_summary: str

    def to_dict(self) -> dict[str, object]:
        """
        JSON-serializable representation.
        """
        return {
            "scenario_id": self.scenario_id,
            "overall_status": self.overall_status,
            "primary_cause_class": self.primary_cause_class,
            "primary_confidence": round(self.primary_confidence, 6),
            "affected_surfaces": list(self.affected_surfaces),
            "preliminary_recommended_actions": list(self.preliminary_recommended_actions),
            "preliminary_blocked_actions": list(self.preliminary_blocked_actions),
            "operator_summary": self.operator_summary,
            "hypotheses": [hypothesis.to_dict() for hypothesis in self.hypotheses],
        }

    def summary(self) -> dict[str, object]:
        """
        Compact summary for CLI output.
        """
        return {
            "scenario_id": self.scenario_id,
            "overall_status": self.overall_status,
            "primary_cause_class": self.primary_cause_class,
            "primary_confidence": round(self.primary_confidence, 6),
            "preliminary_recommended_actions": list(self.preliminary_recommended_actions),
            "preliminary_blocked_actions": list(self.preliminary_blocked_actions),
            "top_hypotheses": [
                {
                    "cause_class": hypothesis.cause_class,
                    "score": round(hypothesis.score, 6),
                }
                for hypothesis in self.hypotheses[:3]
            ],
        }


def _finding_map(findings: tuple[SentinelFinding, ...]) -> dict[str, SentinelFinding]:
    return {finding.category: finding for finding in findings}


def _fault_types_from_replay(result: ReplayResult) -> set[str]:
    fault_types: set[str] = set()
    for event in result.events:
        if event.event_type != "fault_effects_resolved":
            continue
        details = event.details
        raw = details.get("fault_types", [])
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, str):
                    fault_types.add(item)
    return fault_types


def _dominant_factors_from_replay(result: ReplayResult) -> set[str]:
    factors: set[str] = set()
    for sample in result.samples:
        for factor in sample.dominant_confidence_factors:
            factors.add(factor)
    return factors


def _seed_scores(
    result: ReplayResult,
    sentinel: SentinelReport,
) -> tuple[dict[str, float], dict[str, list[str]], dict[str, set[str]]]:
    scores = {cause: 0.05 for cause in CAUSE_CLASSES}
    rationales: dict[str, list[str]] = {cause: [] for cause in CAUSE_CLASSES}
    categories: dict[str, set[str]] = {cause: set() for cause in CAUSE_CLASSES}

    if result.cause_class_hint in scores:
        scores[result.cause_class_hint] += 0.30
        rationales[result.cause_class_hint].append(
            "Replay harness emitted this cause-class hint at the first anomaly threshold."
        )

    findings = _finding_map(sentinel.findings)
    fault_types = _fault_types_from_replay(result)
    dominant_factors = _dominant_factors_from_replay(result)

    if "comm_window" in findings:
        scores["link_state_degradation"] += 0.28
        rationales["link_state_degradation"].append(
            "Communication-window availability degraded during replay."
        )
        categories["link_state_degradation"].add("comm_window")

    if "pointing_error" in findings:
        scores["pointing_state_inconsistency"] += 0.32
        rationales["pointing_state_inconsistency"].append(
            "Pointing error crossed bounded trust thresholds."
        )
        categories["pointing_state_inconsistency"].add("pointing_error")

    if "telemetry_freshness" in findings:
        scores["timing_drift_or_stale_data"] += 0.24
        rationales["timing_drift_or_stale_data"].append(
            "Telemetry freshness exceeded bounded trust thresholds."
        )
        categories["timing_drift_or_stale_data"].add("telemetry_freshness")

    if "clock_bias" in findings:
        scores["timing_drift_or_stale_data"] += 0.30
        rationales["timing_drift_or_stale_data"].append(
            "Clock bias exceeded bounded trust thresholds."
        )
        categories["timing_drift_or_stale_data"].add("clock_bias")

    if "multi_fault_pressure" in findings:
        scores["recovery_attempt_risk_escalation"] += 0.10
        rationales["recovery_attempt_risk_escalation"].append(
            "Overlapping fault pressure increases unsafe recovery risk."
        )
        categories["recovery_attempt_risk_escalation"].add("multi_fault_pressure")

    if "packet_loss" in fault_types or "dropout" in fault_types:
        scores["link_state_degradation"] += 0.34
        rationales["link_state_degradation"].append(
            "Resolved fault effects included packet-loss or dropout pressure."
        )

    if "pointing_drift" in fault_types:
        scores["pointing_state_inconsistency"] += 0.30
        rationales["pointing_state_inconsistency"].append(
            "Resolved fault effects included pointing-drift pressure."
        )

    if "sensor_stale" in fault_types:
        scores["timing_drift_or_stale_data"] += 0.18
        rationales["timing_drift_or_stale_data"].append(
            "Resolved fault effects included stale-sensor pressure."
        )

    if "clock_bias_growth" in fault_types:
        scores["timing_drift_or_stale_data"] += 0.22
        rationales["timing_drift_or_stale_data"].append(
            "Resolved fault effects included growing clock-bias pressure."
        )

    if "sensor_bias" in fault_types:
        scores["sensor_disagreement_or_corruption"] += 0.36
        rationales["sensor_disagreement_or_corruption"].append(
            "Resolved fault effects included sensor-bias pressure."
        )

    if "mode_mismatch" in fault_types:
        scores["recovery_attempt_risk_escalation"] += 0.34
        rationales["recovery_attempt_risk_escalation"].append(
            "Resolved fault effects included mode-mismatch pressure."
        )

    if "dropout" in dominant_factors or "closed_comm_window" in dominant_factors:
        scores["link_state_degradation"] += 0.12
        rationales["link_state_degradation"].append(
            "Dominant confidence degradation factors were link-adjacent."
        )

    if "pointing_error" in dominant_factors:
        scores["pointing_state_inconsistency"] += 0.12
        rationales["pointing_state_inconsistency"].append(
            "Dominant confidence degradation factors were pointing-linked."
        )

    if "telemetry_freshness" in dominant_factors or "clock_bias" in dominant_factors:
        scores["timing_drift_or_stale_data"] += 0.12
        rationales["timing_drift_or_stale_data"].append(
            "Dominant confidence degradation factors were timing or freshness-linked."
        )

    if "sensor_bias" in dominant_factors:
        scores["sensor_disagreement_or_corruption"] += 0.10
        rationales["sensor_disagreement_or_corruption"].append(
            "Dominant confidence degradation factors included sensor-bias pressure."
        )

    if "mode_mismatch" in dominant_factors:
        scores["recovery_attempt_risk_escalation"] += 0.10
        rationales["recovery_attempt_risk_escalation"].append(
            "Dominant confidence degradation factors included mode-mismatch pressure."
        )

    if "line_confidence" in findings:
        line_finding = findings["line_confidence"]
        if line_finding.status in {"critical", "degraded"}:
            scores["link_state_degradation"] += 0.08
            scores["pointing_state_inconsistency"] += 0.06
            scores["timing_drift_or_stale_data"] += 0.04
            categories["link_state_degradation"].add("line_confidence")
            categories["pointing_state_inconsistency"].add("line_confidence")
            categories["timing_drift_or_stale_data"].add("line_confidence")

    return scores, rationales, categories


def _rank_hypotheses(
    scores: dict[str, float],
    rationales: dict[str, list[str]],
    categories: dict[str, set[str]],
) -> tuple[TriageHypothesis, ...]:
    total = sum(scores.values())
    if total <= 0.0:
        total = 1.0

    hypotheses: list[TriageHypothesis] = []
    for cause_class, raw_score in scores.items():
        normalized = raw_score / total
        rationale = tuple(rationales[cause_class]) or (
            "Bounded triage found only weak support for this cause class.",
        )
        supporting_categories = tuple(sorted(categories[cause_class]))
        hypotheses.append(
            TriageHypothesis(
                cause_class=cause_class,
                score=normalized,
                rationale=rationale,
                supporting_categories=supporting_categories,
                affected_surfaces=CAUSE_TO_SURFACES[cause_class],
            )
        )

    hypotheses.sort(key=lambda hypothesis: hypothesis.score, reverse=True)
    return tuple(hypotheses)


def _policy_for(primary_cause_class: str, overall_status: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    policy = PRELIMINARY_POLICY[primary_cause_class]
    if overall_status == "critical":
        recommended = policy["critical_recommended"]
        blocked = policy["critical_blocked"]
    else:
        recommended = policy["recommended"]
        blocked = policy["blocked"]
    return recommended, blocked


def _operator_summary(
    primary: TriageHypothesis,
    second: TriageHypothesis | None,
    overall_status: str,
) -> str:
    ambiguity = ""
    if second is not None and (primary.score - second.score) <= 0.12:
        ambiguity = (
            f" Secondary pressure remains non-trivial from {second.cause_class.replace('_', ' ')}."
        )

    return (
        f"Overall posture is {overall_status}. Primary bounded hypothesis is "
        f"{primary.cause_class.replace('_', ' ')} with confidence share "
        f"{primary.score:.2f}. Likely affected surfaces: "
        f"{', '.join(primary.affected_surfaces)}.{ambiguity}"
    )


def triage_replay(result: ReplayResult, sentinel: SentinelReport) -> TriageReport:
    """
    Produce a bounded anomaly-triage report from replay and sentinel evidence.
    """
    scores, rationales, categories = _seed_scores(result, sentinel)
    hypotheses = _rank_hypotheses(scores, rationales, categories)
    primary = hypotheses[0]
    second = hypotheses[1] if len(hypotheses) > 1 else None
    recommended, blocked = _policy_for(primary.cause_class, sentinel.overall_status)

    return TriageReport(
        scenario_id=result.scenario_id,
        overall_status=sentinel.overall_status,
        primary_cause_class=primary.cause_class,
        primary_confidence=primary.score,
        hypotheses=hypotheses,
        affected_surfaces=primary.affected_surfaces,
        preliminary_recommended_actions=recommended,
        preliminary_blocked_actions=blocked,
        operator_summary=_operator_summary(primary, second, sentinel.overall_status),
    )
