from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from ix_dsat.contracts import ALLOWED_ACTIONS
from ix_dsat.replay import ReplayResult
from ix_dsat.scenario import Scenario
from ix_dsat.sentinel import SentinelReport
from ix_dsat.triage import TriageReport


ACTION_SET: Final[set[str]] = set(ALLOWED_ACTIONS)

LATCH_RELEASE_CONDITIONS: Final[dict[str, str]] = {
    "line_confidence_critical": "Release only after minimum line confidence recovers above 0.55.",
    "telemetry_freshness_critical": "Release only after telemetry freshness returns below 12.0 s.",
    "clock_bias_critical": "Release only after clock bias returns below 80.0 ms.",
    "comm_window_loss": "Release only after the communication window remains open and stable.",
    "multi_fault_pressure": "Release only after overlapping active-fault count drops below 3.",
}

CAUSE_SAFE_CORE: Final[dict[str, dict[str, tuple[str, ...]]]] = {
    "link_state_degradation": {
        "degraded": (
            "freeze_high_risk_recovery",
            "await_fresh_state_estimate",
            "switch_to_low_rate_link",
        ),
        "critical": (
            "freeze_high_risk_recovery",
            "await_fresh_state_estimate",
            "switch_to_low_rate_link",
            "shed_noncritical_traffic",
            "enter_safe_comm_posture",
        ),
    },
    "pointing_state_inconsistency": {
        "degraded": (
            "freeze_high_risk_recovery",
            "await_fresh_state_estimate",
            "hold_current_pointing",
        ),
        "critical": (
            "freeze_high_risk_recovery",
            "await_fresh_state_estimate",
            "hold_current_pointing",
        ),
    },
    "timing_drift_or_stale_data": {
        "degraded": (
            "freeze_high_risk_recovery",
            "await_fresh_state_estimate",
            "switch_to_low_rate_link",
        ),
        "critical": (
            "freeze_high_risk_recovery",
            "await_fresh_state_estimate",
            "switch_to_low_rate_link",
            "enter_safe_comm_posture",
        ),
    },
    "sensor_disagreement_or_corruption": {
        "degraded": (
            "freeze_high_risk_recovery",
            "await_fresh_state_estimate",
            "shed_noncritical_traffic",
        ),
        "critical": (
            "freeze_high_risk_recovery",
            "await_fresh_state_estimate",
            "enter_safe_comm_posture",
            "shed_noncritical_traffic",
        ),
    },
    "recovery_attempt_risk_escalation": {
        "degraded": (
            "freeze_high_risk_recovery",
            "await_fresh_state_estimate",
            "hold_current_pointing",
        ),
        "critical": (
            "freeze_high_risk_recovery",
            "await_fresh_state_estimate",
            "enter_safe_comm_posture",
        ),
    },
}


@dataclass(frozen=True, slots=True)
class GateLatch:
    """
    One latched gate condition.
    """

    name: str
    active: bool
    reason: str
    release_condition: str

    def to_dict(self) -> dict[str, object]:
        """
        JSON-serializable representation.
        """
        return {
            "name": self.name,
            "active": self.active,
            "reason": self.reason,
            "release_condition": self.release_condition,
        }


@dataclass(frozen=True, slots=True)
class GateReport:
    """
    Safe-action gate decision.
    """

    scenario_id: str
    overall_status: str
    primary_cause_class: str
    latch_state: str
    active_latches: tuple[GateLatch, ...]
    allowed_actions: tuple[str, ...]
    blocked_actions: tuple[str, ...]
    gate_rationale: tuple[str, ...]
    operator_summary: str

    def to_dict(self) -> dict[str, object]:
        """
        JSON-serializable representation.
        """
        return {
            "scenario_id": self.scenario_id,
            "overall_status": self.overall_status,
            "primary_cause_class": self.primary_cause_class,
            "latch_state": self.latch_state,
            "active_latches": [latch.to_dict() for latch in self.active_latches],
            "allowed_actions": list(self.allowed_actions),
            "blocked_actions": list(self.blocked_actions),
            "gate_rationale": list(self.gate_rationale),
            "operator_summary": self.operator_summary,
        }

    def summary(self) -> dict[str, object]:
        """
        Compact summary for CLI output.
        """
        return {
            "scenario_id": self.scenario_id,
            "overall_status": self.overall_status,
            "primary_cause_class": self.primary_cause_class,
            "latch_state": self.latch_state,
            "active_latch_names": [latch.name for latch in self.active_latches],
            "allowed_actions": list(self.allowed_actions),
            "blocked_actions": list(self.blocked_actions),
        }


def _build_latches(sentinel: SentinelReport) -> tuple[GateLatch, ...]:
    metrics = sentinel.metrics
    latches: list[GateLatch] = []

    minimum_line_confidence = metrics.get("minimum_line_confidence")
    if isinstance(minimum_line_confidence, float) and minimum_line_confidence <= 0.35:
        latches.append(
            GateLatch(
                name="line_confidence_critical",
                active=True,
                reason="Minimum line confidence entered critical trust range.",
                release_condition=LATCH_RELEASE_CONDITIONS["line_confidence_critical"],
            )
        )

    maximum_telemetry_freshness = metrics.get("maximum_telemetry_freshness_s")
    if isinstance(maximum_telemetry_freshness, float) and maximum_telemetry_freshness >= 30.0:
        latches.append(
            GateLatch(
                name="telemetry_freshness_critical",
                active=True,
                reason="Telemetry freshness exceeded critical trust range.",
                release_condition=LATCH_RELEASE_CONDITIONS["telemetry_freshness_critical"],
            )
        )

    maximum_clock_bias = metrics.get("maximum_clock_bias_ms")
    if isinstance(maximum_clock_bias, float) and maximum_clock_bias >= 250.0:
        latches.append(
            GateLatch(
                name="clock_bias_critical",
                active=True,
                reason="Clock bias exceeded critical trust range.",
                release_condition=LATCH_RELEASE_CONDITIONS["clock_bias_critical"],
            )
        )

    comm_window_closed_any = metrics.get("comm_window_closed_any")
    if isinstance(comm_window_closed_any, bool) and comm_window_closed_any:
        latches.append(
            GateLatch(
                name="comm_window_loss",
                active=True,
                reason="Communication window was not continuously available.",
                release_condition=LATCH_RELEASE_CONDITIONS["comm_window_loss"],
            )
        )

    maximum_active_fault_count = metrics.get("maximum_active_fault_count")
    if isinstance(maximum_active_fault_count, int) and maximum_active_fault_count >= 3:
        latches.append(
            GateLatch(
                name="multi_fault_pressure",
                active=True,
                reason="Three or more active faults overlapped during replay.",
                release_condition=LATCH_RELEASE_CONDITIONS["multi_fault_pressure"],
            )
        )

    return tuple(latches)


def _safe_core(primary_cause_class: str, overall_status: str) -> set[str]:
    if overall_status not in {"degraded", "critical"}:
        return set()
    return set(CAUSE_SAFE_CORE[primary_cause_class][overall_status])


def _latched_safe_core(primary_cause_class: str) -> set[str]:
    return set(CAUSE_SAFE_CORE[primary_cause_class]["critical"])


def _mission_actions(scenario: Scenario) -> tuple[set[str], set[str]]:
    return set(scenario.expected.allowed_actions), set(scenario.expected.blocked_actions)


def _operator_summary(
    overall_status: str,
    primary_cause_class: str,
    latch_state: str,
    allowed_actions: tuple[str, ...],
    blocked_actions: tuple[str, ...],
) -> str:
    return (
        f"Overall posture is {overall_status}. Primary bounded cause class is "
        f"{primary_cause_class.replace('_', ' ')}. Gate is {latch_state}. "
        f"Allowed actions now: {', '.join(allowed_actions)}. "
        f"Blocked actions now: {', '.join(blocked_actions)}."
    )


def gate_actions(
    scenario: Scenario,
    result: ReplayResult,
    sentinel: SentinelReport,
    triage: TriageReport,
) -> GateReport:
    """
    Produce a bounded allow/deny action decision with latch behavior.
    """
    mission_allowed, mission_blocked = _mission_actions(scenario)
    triage_recommended = set(triage.preliminary_recommended_actions)
    triage_blocked = set(triage.preliminary_blocked_actions)
    latches = _build_latches(sentinel)
    latch_state = "latched" if latches else "unlatched"

    rationale: list[str] = [
        "Gate starts from scenario envelope, triage posture, and sentinel status.",
        f"Primary cause class is {triage.primary_cause_class}.",
        f"Overall status is {sentinel.overall_status}.",
    ]

    safe_core = _safe_core(triage.primary_cause_class, sentinel.overall_status)
    if safe_core:
        rationale.append("Status-triggered safe-core actions were added to the allow set.")

    if latch_state == "latched":
        safe_core = _latched_safe_core(triage.primary_cause_class)
        rationale.append("Latched critical conditions forced the gate into bounded recovery only.")

    blocked = (mission_blocked | triage_blocked) - safe_core
    allowed = ((mission_allowed & triage_recommended) | safe_core) - blocked

    if latch_state == "latched":
        allowed = allowed & _latched_safe_core(triage.primary_cause_class)
        blocked = (ACTION_SET - allowed) | blocked

    if not allowed:
        fallback = {"freeze_high_risk_recovery", "await_fresh_state_estimate"}
        allowed = fallback
        blocked = ACTION_SET - allowed
        rationale.append("Fallback bounded-recovery pair was forced because no actions remained allowed.")

    allowed_actions = tuple(sorted(allowed))
    blocked_actions = tuple(sorted(ACTION_SET - set(allowed_actions) | blocked))

    rationale.append(
        f"Final gate exposes {len(allowed_actions)} allowed actions and {len(blocked_actions)} blocked actions."
    )
    rationale.append(f"Replay anomaly_detected={result.anomaly_detected}.")

    return GateReport(
        scenario_id=result.scenario_id,
        overall_status=sentinel.overall_status,
        primary_cause_class=triage.primary_cause_class,
        latch_state=latch_state,
        active_latches=latches,
        allowed_actions=allowed_actions,
        blocked_actions=blocked_actions,
        gate_rationale=tuple(rationale),
        operator_summary=_operator_summary(
            sentinel.overall_status,
            triage.primary_cause_class,
            latch_state,
            allowed_actions,
            blocked_actions,
        ),
    )
