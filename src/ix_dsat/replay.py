from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from ix_dsat.faults import FaultEffectAggregate, FaultObservation, resolve_fault_effects
from ix_dsat.scenario import FaultInjection, Scenario


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


@dataclass(frozen=True, slots=True)
class ReplayEvent:
    """
    A deterministic replay event.
    """

    time_s: float
    event_type: str
    severity: float
    message: str
    details: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ReplaySample:
    """
    A sampled state during replay.
    """

    time_s: float
    line_confidence: float
    telemetry_freshness_s: float
    pointing_error_deg: float
    clock_bias_ms: float
    comm_window_open: bool
    active_fault_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReplayResult:
    """
    Full replay result for a deterministic scenario run.
    """

    scenario_id: str
    duration_s: int
    tick_hz: int
    tick_count: int
    anomaly_detected: bool
    first_anomaly_time_s: float | None
    cause_class_hint: str | None
    minimum_line_confidence: float
    final_line_confidence: float
    events: tuple[ReplayEvent, ...]
    samples: tuple[ReplaySample, ...]
    final_state: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """
        Return a JSON-serializable dictionary.
        """
        return {
            "scenario_id": self.scenario_id,
            "duration_s": self.duration_s,
            "tick_hz": self.tick_hz,
            "tick_count": self.tick_count,
            "anomaly_detected": self.anomaly_detected,
            "first_anomaly_time_s": self.first_anomaly_time_s,
            "cause_class_hint": self.cause_class_hint,
            "minimum_line_confidence": self.minimum_line_confidence,
            "final_line_confidence": self.final_line_confidence,
            "event_count": len(self.events),
            "sample_count": len(self.samples),
            "events": [asdict(event) for event in self.events],
            "samples": [asdict(sample) for sample in self.samples],
            "final_state": self.final_state,
        }

    def summary(self) -> dict[str, Any]:
        """
        Return a compact replay summary for CLI output.
        """
        return {
            "scenario_id": self.scenario_id,
            "duration_s": self.duration_s,
            "tick_hz": self.tick_hz,
            "tick_count": self.tick_count,
            "anomaly_detected": self.anomaly_detected,
            "first_anomaly_time_s": self.first_anomaly_time_s,
            "cause_class_hint": self.cause_class_hint,
            "minimum_line_confidence": round(self.minimum_line_confidence, 6),
            "final_line_confidence": round(self.final_line_confidence, 6),
            "event_types": [event.event_type for event in self.events],
            "final_state": self.final_state,
        }


def _initial_channel_values(scenario: Scenario) -> dict[str, str | float | bool]:
    return {channel.name: channel.initial_value for channel in scenario.telemetry_channels}


def _active_faults(scenario: Scenario, time_s: float) -> tuple[FaultInjection, ...]:
    active: list[FaultInjection] = []
    for fault in scenario.faults:
        starts = time_s >= fault.start_s
        ends = fault.end_s is None or time_s <= fault.end_s
        if starts and ends:
            active.append(fault)
    return tuple(sorted(active, key=lambda item: (item.start_s, item.fault_id))))


def _sync_named_channels(state: dict[str, Any], channels: dict[str, Any]) -> None:
    if "line_confidence" in channels:
        channels["line_confidence"] = state["line_confidence"]
    if "pointing_error_deg" in channels:
        channels["pointing_error_deg"] = state["pointing_error_deg"]
    if "telemetry_freshness_s" in channels:
        channels["telemetry_freshness_s"] = state["telemetry_freshness_s"]
    if "comm_window_open" in channels:
        channels["comm_window_open"] = state["comm_window_open"]
    if "link_mode" in channels:
        channels["link_mode"] = state["link_mode"]


def _infer_cause_class(active_faults: tuple[FaultInjection, ...], state: dict[str, Any]) -> str:
    active_types = {fault.fault_type for fault in active_faults}

    if "packet_loss" in active_types or "dropout" in active_types:
        return "link_state_degradation"
    if "pointing_drift" in active_types or state["pointing_error_deg"] > 2.0:
        return "pointing_state_inconsistency"
    if "clock_bias_growth" in active_types or state["telemetry_freshness_s"] > 8.0:
        return "timing_drift_or_stale_data"
    if "sensor_bias" in active_types or "sensor_stale" in active_types:
        return "sensor_disagreement_or_corruption"
    if "mode_mismatch" in active_types:
        return "recovery_attempt_risk_escalation"
    return "link_state_degradation"


def _compute_line_confidence(
    baseline: float,
    state: dict[str, Any],
    effects: FaultEffectAggregate,
) -> float:
    pointing_penalty = min(0.72, max(0.0, state["pointing_error_deg"] - 0.25) * 0.18)
    freshness_penalty = min(
        0.18,
        max(0.0, state["telemetry_freshness_s"] - 0.75) * 0.012,
    )
    clock_penalty = min(0.12, max(0.0, state["clock_bias_ms"] - 2.0) * 0.0006)
    packet_penalty = min(0.25, effects.packet_loss_ratio * 0.6)
    bias_penalty = min(0.20, effects.sensor_bias_level * 0.20)
    mismatch_penalty = min(0.18, effects.mode_mismatch_level * 0.18)
    dropout_penalty = 0.45 if effects.dropout_level > 0.0 else 0.0
    closed_window_penalty = 0.22 if not state["comm_window_open"] else 0.0

    confidence = baseline
    confidence -= pointing_penalty
    confidence -= freshness_penalty
    confidence -= clock_penalty
    confidence -= packet_penalty
    confidence -= bias_penalty
    confidence -= mismatch_penalty
    confidence -= dropout_penalty
    confidence -= closed_window_penalty
    return _clamp(confidence, 0.0, 1.0)


def _step_state(
    *,
    scenario: Scenario,
    state: dict[str, Any],
    dt_s: float,
    active_faults: tuple[FaultInjection, ...],
) -> tuple[FaultEffectAggregate, tuple[FaultObservation, ...]]:
    effects, observations = resolve_fault_effects(active_faults)

    state["pointing_error_deg"] = _clamp(
        state["pointing_error_deg"] + effects.pointing_drift_deg_per_s * dt_s,
        0.0,
        180.0,
    )

    if effects.stale_growth_s_per_s > 0.0:
        state["telemetry_freshness_s"] = _clamp(
            state["telemetry_freshness_s"] + effects.stale_growth_s_per_s * dt_s,
            0.0,
            3600.0,
        )
    else:
        baseline_freshness = scenario.initial_state.telemetry_freshness_s
        state["telemetry_freshness_s"] = max(
            baseline_freshness,
            state["telemetry_freshness_s"] - (2.0 * dt_s),
        )

    if effects.clock_bias_growth_ms_per_s > 0.0:
        state["clock_bias_ms"] = _clamp(
            state["clock_bias_ms"] + effects.clock_bias_growth_ms_per_s * dt_s,
            0.0,
            60000.0,
        )
    else:
        baseline_clock_bias = scenario.initial_state.clock_bias_ms
        state["clock_bias_ms"] = max(
            baseline_clock_bias,
            state["clock_bias_ms"] - (5.0 * dt_s),
        )

    if effects.dropout_level >= 0.5:
        state["comm_window_open"] = False
        state["link_mode"] = "dropout"
    else:
        state["comm_window_open"] = scenario.initial_state.comm_window_open
        if effects.packet_loss_ratio >= 0.10:
            state["link_mode"] = "degraded"
        else:
            state["link_mode"] = "nominal"

    state["line_confidence"] = _compute_line_confidence(
        baseline=scenario.initial_state.line_confidence,
        state=state,
        effects=effects,
    )

    _sync_named_channels(state=state, channels=state["channels"])
    return effects, observations


def replay_scenario(scenario: Scenario, sample_every_n_ticks: int = 1) -> ReplayResult:
    """
    Execute a deterministic replay for a validated scenario.

    Args:
        scenario:
            The validated scenario to execute.
        sample_every_n_ticks:
            Keep every Nth tick as a sample. Values <= 0 are treated as 1.

    Returns:
        ReplayResult containing event stream, summary values, and final state.
    """
    sample_stride = max(1, int(sample_every_n_ticks))
    dt_s = 1.0 / float(scenario.timeline.tick_hz)
    total_ticks = int(scenario.timeline.duration_s * scenario.timeline.tick_hz) + 1

    state: dict[str, Any] = {
        "line_confidence": scenario.initial_state.line_confidence,
        "telemetry_freshness_s": scenario.initial_state.telemetry_freshness_s,
        "pointing_error_deg": scenario.initial_state.pointing_error_deg,
        "clock_bias_ms": scenario.initial_state.clock_bias_ms,
        "comm_window_open": scenario.initial_state.comm_window_open,
        "vehicle_mode": scenario.initial_state.vehicle_mode,
        "link_mode": "nominal",
        "channels": _initial_channel_values(scenario),
    }
    _sync_named_channels(state=state, channels=state["channels"])

    events: list[ReplayEvent] = [
        ReplayEvent(
            time_s=0.0,
            event_type="scenario_started",
            severity=0.0,
            message="Deterministic replay started.",
            details={
                "scenario_id": scenario.scenario_id,
                "duration_s": scenario.timeline.duration_s,
                "tick_hz": scenario.timeline.tick_hz,
            },
        )
    ]
    samples: list[ReplaySample] = []
    minimum_line_confidence = state["line_confidence"]
    anomaly_detected = False
    first_anomaly_time_s: float | None = None
    cause_class_hint: str | None = None
    emitted_event_types = {"scenario_started"}

    for tick_index in range(total_ticks):
        time_s = round(tick_index * dt_s, 6)
        active_faults = _active_faults(scenario, time_s)

        if tick_index > 0:
            effects, observations = _step_state(
                scenario=scenario,
                state=state,
                dt_s=dt_s,
                active_faults=active_faults,
            )
        else:
            effects, observations = resolve_fault_effects(active_faults)

        if observations:
            events.append(
                ReplayEvent(
                    time_s=time_s,
                    event_type="fault_effects_resolved",
                    severity=max(obs.severity for obs in observations),
                    message="Seeded fault library resolved active effects.",
                    details={
                        "fault_count": len(observations),
                        "fault_ids": [obs.fault_id for obs in observations],
                        "fault_types": [obs.fault_type for obs in observations],
                        "effects": effects.to_dict(),
                    },
                )
            )

        minimum_line_confidence = min(minimum_line_confidence, state["line_confidence"])

        anomaly_triggered = (
            state["line_confidence"] < 0.78
            or state["pointing_error_deg"] > 1.5
            or state["telemetry_freshness_s"] > 6.0
            or effects.dropout_level > 0.0
        )

        if anomaly_triggered and not anomaly_detected:
            anomaly_detected = True
            first_anomaly_time_s = time_s
            cause_class_hint = _infer_cause_class(active_faults=active_faults, state=state)
            events.append(
                ReplayEvent(
                    time_s=time_s,
                    event_type="anomaly_detected",
                    severity=round(1.0 - state["line_confidence"], 6),
                    message="Replay crossed anomaly threshold.",
                    details={
                        "line_confidence": round(state["line_confidence"], 6),
                        "pointing_error_deg": round(state["pointing_error_deg"], 6),
                        "telemetry_freshness_s": round(state["telemetry_freshness_s"], 6),
                        "active_fault_ids": [fault.fault_id for fault in active_faults],
                    },
                )
            )
            events.append(
                ReplayEvent(
                    time_s=time_s,
                    event_type="triage_emitted",
                    severity=round(1.0 - state["line_confidence"], 6),
                    message="Replay emitted a first-pass cause-class hint.",
                    details={
                        "cause_class_hint": cause_class_hint,
                        "line_confidence": round(state["line_confidence"], 6),
                    },
                )
            )
            emitted_event_types.update({"anomaly_detected", "triage_emitted"})

        if anomaly_detected and "confidence_degraded" not in emitted_event_types:
            if state["line_confidence"] <= 0.50:
                events.append(
                    ReplayEvent(
                        time_s=time_s,
                        event_type="confidence_degraded",
                        severity=round(1.0 - state["line_confidence"], 6),
                        message="Replay confidence dropped into degraded range.",
                        details={"line_confidence": round(state["line_confidence"], 6)},
                    )
                )
                emitted_event_types.add("confidence_degraded")

        if anomaly_detected and "recovery_action_bounded" not in emitted_event_types:
            if state["line_confidence"] <= (scenario.expected.minimum_confidence_floor + 0.10):
                events.append(
                    ReplayEvent(
                        time_s=time_s,
                        event_type="recovery_action_bounded",
                        severity=round(1.0 - state["line_confidence"], 6),
                        message="Replay entered bounded-recovery posture.",
                        details={
                            "allowed_actions": list(scenario.expected.allowed_actions),
                            "blocked_actions": list(scenario.expected.blocked_actions),
                            "line_confidence": round(state["line_confidence"], 6),
                        },
                    )
                )
                emitted_event_types.add("recovery_action_bounded")

        if tick_index % sample_stride == 0:
            samples.append(
                ReplaySample(
                    time_s=time_s,
                    line_confidence=round(state["line_confidence"], 6),
                    telemetry_freshness_s=round(state["telemetry_freshness_s"], 6),
                    pointing_error_deg=round(state["pointing_error_deg"], 6),
                    clock_bias_ms=round(state["clock_bias_ms"], 6),
                    comm_window_open=state["comm_window_open"],
                    active_fault_ids=tuple(fault.fault_id for fault in active_faults),
                )
            )

    final_state = {
        "line_confidence": round(state["line_confidence"], 6),
        "telemetry_freshness_s": round(state["telemetry_freshness_s"], 6),
        "pointing_error_deg": round(state["pointing_error_deg"], 6),
        "clock_bias_ms": round(state["clock_bias_ms"], 6),
        "comm_window_open": state["comm_window_open"],
        "vehicle_mode": state["vehicle_mode"],
        "link_mode": state["link_mode"],
    }

    return ReplayResult(
        scenario_id=scenario.scenario_id,
        duration_s=scenario.timeline.duration_s,
        tick_hz=scenario.timeline.tick_hz,
        tick_count=total_ticks,
        anomaly_detected=anomaly_detected,
        first_anomaly_time_s=first_anomaly_time_s,
        cause_class_hint=cause_class_hint,
        minimum_line_confidence=minimum_line_confidence,
        final_line_confidence=state["line_confidence"],
        events=tuple(events),
        samples=tuple(samples),
        final_state=final_state,
    )
