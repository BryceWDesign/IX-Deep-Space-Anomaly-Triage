from __future__ import annotations

from dataclasses import dataclass

from ix_dsat.gate import GateReport
from ix_dsat.ledger import EvidenceLedger
from ix_dsat.replay import ReplayEvent, ReplayResult
from ix_dsat.scenario import Scenario
from ix_dsat.sentinel import SentinelReport
from ix_dsat.sync_queue import DelayTolerantSyncQueue
from ix_dsat.triage import TriageReport


def _event_time(events: tuple[ReplayEvent, ...], event_type: str) -> float | None:
    for event in events:
        if event.event_type == event_type:
            return event.time_s
    return None


def _required_event_coverage(
    scenario: Scenario, replay: ReplayResult
) -> tuple[float, tuple[str, ...]]:
    emitted = {event.event_type for event in replay.events}
    required = scenario.expected.must_emit_events
    if not required:
        return 1.0, ()
    missing = tuple(sorted(event_name for event_name in required if event_name not in emitted))
    covered = len(required) - len(missing)
    return covered / len(required), missing


@dataclass(frozen=True, slots=True)
class MetricsReport:
    """
    End-to-end validation metrics for one DSAT scenario execution.
    """

    scenario_id: str
    anomaly_detected: bool
    anomaly_to_triage_latency_s: float | None
    minimum_line_confidence: float
    expected_confidence_floor: float
    confidence_margin_to_floor: float
    confidence_floor_crossed: bool
    primary_cause_class: str
    expected_cause_class: str
    primary_cause_match: bool
    replay_cause_hint_match: bool
    hypothesis_separation: float
    required_event_coverage_ratio: float
    missing_required_events: tuple[str, ...]
    allowed_action_count: int
    blocked_action_count: int
    active_latch_count: int
    latch_state: str
    ledger_record_count: int
    sync_envelope_count: int
    first_sync_priority: str | None

    def to_dict(self) -> dict[str, object]:
        """
        JSON-serializable representation.
        """
        return {
            "scenario_id": self.scenario_id,
            "anomaly_detected": self.anomaly_detected,
            "anomaly_to_triage_latency_s": self.anomaly_to_triage_latency_s,
            "minimum_line_confidence": round(self.minimum_line_confidence, 6),
            "expected_confidence_floor": round(self.expected_confidence_floor, 6),
            "confidence_margin_to_floor": round(self.confidence_margin_to_floor, 6),
            "confidence_floor_crossed": self.confidence_floor_crossed,
            "primary_cause_class": self.primary_cause_class,
            "expected_cause_class": self.expected_cause_class,
            "primary_cause_match": self.primary_cause_match,
            "replay_cause_hint_match": self.replay_cause_hint_match,
            "hypothesis_separation": round(self.hypothesis_separation, 6),
            "required_event_coverage_ratio": round(self.required_event_coverage_ratio, 6),
            "missing_required_events": list(self.missing_required_events),
            "allowed_action_count": self.allowed_action_count,
            "blocked_action_count": self.blocked_action_count,
            "active_latch_count": self.active_latch_count,
            "latch_state": self.latch_state,
            "ledger_record_count": self.ledger_record_count,
            "sync_envelope_count": self.sync_envelope_count,
            "first_sync_priority": self.first_sync_priority,
        }

    def summary(self) -> dict[str, object]:
        """
        Compact summary for CLI output.
        """
        return {
            "scenario_id": self.scenario_id,
            "anomaly_detected": self.anomaly_detected,
            "anomaly_to_triage_latency_s": self.anomaly_to_triage_latency_s,
            "primary_cause_class": self.primary_cause_class,
            "expected_cause_class": self.expected_cause_class,
            "primary_cause_match": self.primary_cause_match,
            "confidence_floor_crossed": self.confidence_floor_crossed,
            "required_event_coverage_ratio": round(self.required_event_coverage_ratio, 6),
            "active_latch_count": self.active_latch_count,
            "latch_state": self.latch_state,
            "ledger_record_count": self.ledger_record_count,
            "sync_envelope_count": self.sync_envelope_count,
            "first_sync_priority": self.first_sync_priority,
        }


def compute_metrics(
    scenario: Scenario,
    replay: ReplayResult,
    sentinel: SentinelReport,
    triage: TriageReport,
    gate: GateReport,
    ledger: EvidenceLedger,
    sync_queue: DelayTolerantSyncQueue,
) -> MetricsReport:
    """
    Compute bounded end-to-end metrics for one DSAT scenario execution.
    """
    anomaly_time = _event_time(replay.events, "anomaly_detected")
    triage_time = _event_time(replay.events, "triage_emitted")
    if anomaly_time is None or triage_time is None:
        anomaly_to_triage_latency_s = None
    else:
        anomaly_to_triage_latency_s = round(triage_time - anomaly_time, 6)

    required_event_coverage_ratio, missing_required_events = _required_event_coverage(scenario, replay)

    hypothesis_separation = 0.0
    if len(triage.hypotheses) >= 2:
        hypothesis_separation = triage.hypotheses[0].score - triage.hypotheses[1].score

    expected_floor = scenario.expected.minimum_confidence_floor
    confidence_margin_to_floor = replay.minimum_line_confidence - expected_floor
    confidence_floor_crossed = replay.minimum_line_confidence <= expected_floor

    first_sync_priority = sync_queue.envelopes[0].priority if sync_queue.envelopes else None

    _ = sentinel  # reserved for future metric expansion

    return MetricsReport(
        scenario_id=scenario.scenario_id,
        anomaly_detected=replay.anomaly_detected,
        anomaly_to_triage_latency_s=anomaly_to_triage_latency_s,
        minimum_line_confidence=replay.minimum_line_confidence,
        expected_confidence_floor=expected_floor,
        confidence_margin_to_floor=confidence_margin_to_floor,
        confidence_floor_crossed=confidence_floor_crossed,
        primary_cause_class=triage.primary_cause_class,
        expected_cause_class=scenario.expected.cause_class,
        primary_cause_match=(triage.primary_cause_class == scenario.expected.cause_class),
        replay_cause_hint_match=(replay.cause_class_hint == scenario.expected.cause_class),
        hypothesis_separation=hypothesis_separation,
        required_event_coverage_ratio=required_event_coverage_ratio,
        missing_required_events=missing_required_events,
        allowed_action_count=len(gate.allowed_actions),
        blocked_action_count=len(gate.blocked_actions),
        active_latch_count=len(gate.active_latches),
        latch_state=gate.latch_state,
        ledger_record_count=ledger.record_count,
        sync_envelope_count=sync_queue.envelope_count,
        first_sync_priority=first_sync_priority,
    )
