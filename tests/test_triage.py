from ix_dsat.replay import replay_scenario
from ix_dsat.scenario import load_scenario
from ix_dsat.sentinel import scan_replay
from ix_dsat.triage import triage_replay


def test_triage_prefers_link_state_degradation_for_link_scenario() -> None:
    scenario = load_scenario("scenarios/examples/link_state_pointing_drift.json")
    replay = replay_scenario(scenario, sample_every_n_ticks=10)
    sentinel = scan_replay(replay)
    report = triage_replay(replay, sentinel)

    assert report.primary_cause_class == "link_state_degradation"
    assert report.primary_confidence > 0.30
    assert "switch_to_low_rate_link" in report.preliminary_recommended_actions
    assert "communications continuity" in report.affected_surfaces


def test_triage_prefers_timing_drift_for_timing_scenario() -> None:
    scenario = load_scenario("scenarios/examples/timing_bias_growth.json")
    replay = replay_scenario(scenario, sample_every_n_ticks=10)
    sentinel = scan_replay(replay)
    report = triage_replay(replay, sentinel)

    assert report.primary_cause_class == "timing_drift_or_stale_data"
    assert report.primary_confidence > 0.35
    assert "await_fresh_state_estimate" in report.preliminary_recommended_actions
    assert "temporal alignment" in report.affected_surfaces


def test_triage_keeps_ranked_hypotheses_and_operator_summary() -> None:
    scenario = load_scenario("scenarios/examples/link_state_pointing_drift.json")
    replay = replay_scenario(scenario, sample_every_n_ticks=10)
    sentinel = scan_replay(replay)
    report = triage_replay(replay, sentinel)

    assert len(report.hypotheses) == 5
    assert report.hypotheses[0].score >= report.hypotheses[1].score
    assert "Primary bounded hypothesis is" in report.operator_summary
