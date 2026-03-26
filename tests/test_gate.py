from ix_dsat.gate import gate_actions
from ix_dsat.replay import replay_scenario
from ix_dsat.scenario import load_scenario
from ix_dsat.sentinel import scan_replay
from ix_dsat.triage import triage_replay


def test_gate_latches_link_state_scenario_into_bounded_recovery() -> None:
    scenario = load_scenario("scenarios/examples/link_state_pointing_drift.json")
    replay = replay_scenario(scenario, sample_every_n_ticks=10)
    sentinel = scan_replay(replay)
    triage = triage_replay(replay, sentinel)
    gate = gate_actions(scenario, replay, sentinel, triage)

    assert gate.latch_state == "latched"
    assert gate.primary_cause_class == "link_state_degradation"
    assert "freeze_high_risk_recovery" in gate.allowed_actions
    assert "await_fresh_state_estimate" in gate.allowed_actions
    assert "request_reacquisition" in gate.blocked_actions
    assert any(latch.name == "line_confidence_critical" for latch in gate.active_latches)
    assert any(latch.name == "comm_window_loss" for latch in gate.active_latches)


def test_gate_latches_timing_scenario_and_blocks_reacquisition() -> None:
    scenario = load_scenario("scenarios/examples/timing_bias_growth.json")
    replay = replay_scenario(scenario, sample_every_n_ticks=10)
    sentinel = scan_replay(replay)
    triage = triage_replay(replay, sentinel)
    gate = gate_actions(scenario, replay, sentinel, triage)

    assert gate.latch_state == "latched"
    assert gate.primary_cause_class == "timing_drift_or_stale_data"
    assert "await_fresh_state_estimate" in gate.allowed_actions
    assert "freeze_high_risk_recovery" in gate.allowed_actions
    assert "request_reacquisition" in gate.blocked_actions
    assert any(latch.name == "clock_bias_critical" for latch in gate.active_latches)
    assert any(latch.name == "telemetry_freshness_critical" for latch in gate.active_latches)
