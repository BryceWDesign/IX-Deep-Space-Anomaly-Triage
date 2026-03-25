from ix_dsat.replay import replay_scenario
from ix_dsat.scenario import load_scenario


def test_replay_is_deterministic() -> None:
    scenario = load_scenario("scenarios/examples/link_state_pointing_drift.json")
    result_a = replay_scenario(scenario, sample_every_n_ticks=10)
    result_b = replay_scenario(scenario, sample_every_n_ticks=10)
    assert result_a.summary() == result_b.summary()


def test_replay_emits_expected_backbone_events() -> None:
    scenario = load_scenario("scenarios/examples/link_state_pointing_drift.json")
    result = replay_scenario(scenario, sample_every_n_ticks=10)

    event_types = [event.event_type for event in result.events]
    assert "scenario_started" in event_types
    assert "anomaly_detected" in event_types
    assert "triage_emitted" in event_types
    assert "confidence_degraded" in event_types
    assert "recovery_action_bounded" in event_types


def test_replay_reaches_link_state_degradation_hint() -> None:
    scenario = load_scenario("scenarios/examples/link_state_pointing_drift.json")
    result = replay_scenario(scenario, sample_every_n_ticks=10)

    assert result.anomaly_detected is True
    assert result.first_anomaly_time_s == 70.0
    assert result.cause_class_hint == "link_state_degradation"
    assert result.minimum_line_confidence < 0.35
    assert result.final_state["link_mode"] == "degraded"


def test_replay_sample_stride_changes_sample_count_only() -> None:
    scenario = load_scenario("scenarios/examples/link_state_pointing_drift.json")
    dense = replay_scenario(scenario, sample_every_n_ticks=1)
    sparse = replay_scenario(scenario, sample_every_n_ticks=20)

    assert dense.tick_count == sparse.tick_count
    assert len(dense.samples) > len(sparse.samples)
    assert dense.cause_class_hint == sparse.cause_class_hint
