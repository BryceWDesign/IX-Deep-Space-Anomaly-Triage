from __future__ import annotations

from dataclasses import dataclass

from ix_dsat.gate import GateReport
from ix_dsat.metrics import MetricsReport
from ix_dsat.sync_queue import DelayTolerantSyncQueue


@dataclass(frozen=True, slots=True)
class ValidationCheck:
    """
    One explicit pass/fail validation check.
    """

    name: str
    passed: bool
    observed: object
    expected: object
    message: str

    def to_dict(self) -> dict[str, object]:
        """
        JSON-serializable representation.
        """
        return {
            "name": self.name,
            "passed": self.passed,
            "observed": self.observed,
            "expected": self.expected,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """
    End-to-end DSAT validation report.
    """

    scenario_id: str
    passed: bool
    checks: tuple[ValidationCheck, ...]
    metrics: MetricsReport

    def to_dict(self) -> dict[str, object]:
        """
        JSON-serializable representation.
        """
        return {
            "scenario_id": self.scenario_id,
            "passed": self.passed,
            "check_count": len(self.checks),
            "checks": [check.to_dict() for check in self.checks],
            "metrics": self.metrics.to_dict(),
        }

    def summary(self) -> dict[str, object]:
        """
        Compact summary for CLI output.
        """
        return {
            "scenario_id": self.scenario_id,
            "passed": self.passed,
            "check_count": len(self.checks),
            "passed_check_count": sum(1 for check in self.checks if check.passed),
            "failed_checks": [check.name for check in self.checks if not check.passed],
            "primary_cause_match": self.metrics.primary_cause_match,
            "required_event_coverage_ratio": round(self.metrics.required_event_coverage_ratio, 6),
            "latch_state": self.metrics.latch_state,
            "first_sync_priority": self.metrics.first_sync_priority,
        }


def validate_run(
    metrics: MetricsReport,
    gate: GateReport,
    sync_queue: DelayTolerantSyncQueue,
) -> ValidationReport:
    """
    Build an explicit pass/fail validation report from DSAT execution outputs.
    """
    checks = [
        ValidationCheck(
            name="anomaly_detected",
            passed=metrics.anomaly_detected,
            observed=metrics.anomaly_detected,
            expected=True,
            message="Replay must cross an anomaly threshold for the seeded-fault scenario.",
        ),
        ValidationCheck(
            name="primary_cause_match",
            passed=metrics.primary_cause_match,
            observed=metrics.primary_cause_class,
            expected=metrics.expected_cause_class,
            message="Primary triage cause class should match the scenario's expected cause class.",
        ),
        ValidationCheck(
            name="replay_cause_hint_match",
            passed=metrics.replay_cause_hint_match,
            observed=metrics.replay_cause_hint_match,
            expected=True,
            message="Replay cause-class hint should agree with the scenario's expected cause class.",
        ),
        ValidationCheck(
            name="required_events_covered",
            passed=(metrics.required_event_coverage_ratio == 1.0),
            observed=metrics.required_event_coverage_ratio,
            expected=1.0,
            message="Replay must emit every required event declared by the scenario contract.",
        ),
        ValidationCheck(
            name="confidence_floor_crossed",
            passed=metrics.confidence_floor_crossed,
            observed=metrics.confidence_floor_crossed,
            expected=True,
            message="Scenario should drive minimum line confidence through the declared confidence floor.",
        ),
        ValidationCheck(
            name="gate_latched_when_floor_crossed",
            passed=(not metrics.confidence_floor_crossed) or (metrics.latch_state == "latched"),
            observed=metrics.latch_state,
            expected="latched",
            message="Critical or floor-crossing scenarios should latch the gate into bounded recovery.",
        ),
        ValidationCheck(
            name="bounded_recovery_core_present",
            passed=(
                "freeze_high_risk_recovery" in gate.allowed_actions
                and "await_fresh_state_estimate" in gate.allowed_actions
            ),
            observed=list(gate.allowed_actions),
            expected=["freeze_high_risk_recovery", "await_fresh_state_estimate"],
            message="Gate must expose the bounded-recovery core actions.",
        ),
        ValidationCheck(
            name="hypothesis_separation_positive",
            passed=(metrics.hypothesis_separation > 0.0),
            observed=metrics.hypothesis_separation,
            expected="> 0.0",
            message="Primary triage hypothesis should outrank the next hypothesis.",
        ),
        ValidationCheck(
            name="ledger_populated",
            passed=(metrics.ledger_record_count >= 6),
            observed=metrics.ledger_record_count,
            expected=">= 6",
            message="Evidence ledger must contain the scenario contract, replay, sentinel, triage, and gate outputs.",
        ),
        ValidationCheck(
            name="sync_queue_priority_head",
            passed=(metrics.first_sync_priority == "critical"),
            observed=metrics.first_sync_priority,
            expected="critical",
            message="Delay-tolerant sync should prioritize critical evidence first.",
        ),
        ValidationCheck(
            name="sync_queue_populated",
            passed=(sync_queue.envelope_count > 0),
            observed=sync_queue.envelope_count,
            expected="> 0",
            message="Delay-tolerant sync queue must produce at least one envelope.",
        ),
    ]

    passed = all(check.passed for check in checks)
    return ValidationReport(
        scenario_id=metrics.scenario_id,
        passed=passed,
        checks=tuple(checks),
        metrics=metrics,
    )
