from ix_dsat.replay import ReplayEvent, ReplayResult, ReplaySample, replay_scenario
from ix_dsat.scenario import load_scenario
from ix_dsat.sentinel import scan_replay


def test_sentinel_reports_nominal_when_thresholds_are_not_crossed() -> None:
    result = ReplayResult(
        scenario_id="nominal-test",
        duration_s=10,
        tick_hz=1,
        tick_count=11,
        anomaly_detected=False,
        first_anomaly_time_s=None,
        cause_class_hint=None,
        minimum_line_confidence=0.96,
        final_line_confidence=0.96,
        events=(
            ReplayEvent(
                time_s=0.0,
                event_type="scenario_started",
                severity=0.0,
                message="Nominal replay.",
                details={},
            ),
        ),
        samples=(
            ReplaySample(
                time_s=0.0,
                line_confidence=0.96,
                telemetry_freshness_s=0.4,
                pointing_error_deg=0.1,
                clock_bias_ms=2.0,
                comm_window_open=True,
                active_fault_ids=(),
            ),
            ReplaySample(
                time_s=10.0,
                line_confidence=0.95,
                telemetry_freshness_s=0.6,
                pointing_error_deg=0.2,
                clock_bias_ms=3.0,
                comm_window_open=True,
                active_fault_ids=(),
            ),
        ),
        final_state={
            "line_confidence": 0.95,
            "telemetry_freshness_s": 0.6,
            "pointing_error_deg": 0.2,
            "clock_bias_ms": 3.0,
            "comm_window_open": True,
            "vehicle_mode": "relay_tracking",
            "link_mode": "nominal",
        },
    )

    report = scan_replay(result)

    assert report.overall_status == "nominal"
    assert report.recommended_posture == "continue_nominal_ops"
    assert report.findings == ()


def test_sentinel_flags_link_state_pointing_scenario_as_critical() -> None:
    scenario = load_scenario("scenarios/examples/link_state_pointing_drift.json")
    replay = replay_scenario(scenario, sample_every_n_ticks=10)
    report = scan_replay(replay)

    categories = {finding.category for finding in report.findings}

    assert report.overall_status == "critical"
    assert "line_confidence" in categories
    assert "pointing_error" in categories
    assert "telemetry_freshness" in categories
    assert "multi_fault_pressure" in categories


def test_sentinel_flags_timing_bias_scenario_as_critical() -> None:
    scenario = load_scenario("scenarios/examples/timing_bias_growth.json")
    replay = replay_scenario(scenario, sample_every_n_ticks=10)
    report = scan_replay(replay)

    categories = {finding.category for finding in report.findings}

    assert report.overall_status == "critical"
    assert "clock_bias" in categories
    assert "telemetry_freshness" in categories
    assert report.metrics["maximum_clock_bias_ms"] is not None
    assert report.metrics["maximum_telemetry_freshness_s"] is not None
