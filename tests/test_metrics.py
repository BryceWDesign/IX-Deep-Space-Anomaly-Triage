from ix_dsat.gate import gate_actions
from ix_dsat.ledger import build_evidence_ledger
from ix_dsat.metrics import compute_metrics
from ix_dsat.replay import replay_scenario
from ix_dsat.scenario import load_scenario
from ix_dsat.sentinel import scan_replay
from ix_dsat.sync_queue import build_sync_queue
from ix_dsat.triage import triage_replay


def test_metrics_match_expected_link_state_path() -> None:
    scenario = load_scenario("scenarios/examples/link_state_pointing_drift.json")
    replay = replay_scenario(scenario, sample_every_n_ticks=10)
    sentinel = scan_replay(replay)
    triage = triage_replay(replay, sentinel)
    gate = gate_actions(scenario, replay, sentinel, triage)
    ledger = build_evidence_ledger(scenario, replay, sentinel, triage, gate)
    queue = build_sync_queue(ledger)

    metrics = compute_metrics(scenario, replay, sentinel, triage, gate, ledger, queue)

    assert metrics.primary_cause_match is True
    assert metrics.replay_cause_hint_match is True
    assert metrics.required_event_coverage_ratio == 1.0
    assert metrics.confidence_floor_crossed is True
    assert metrics.first_sync_priority == "critical"
    assert metrics.latch_state == "latched"


def test_metrics_match_expected_timing_path() -> None:
    scenario = load_scenario("scenarios/examples/timing_bias_growth.json")
    replay = replay_scenario(scenario, sample_every_n_ticks=10)
    sentinel = scan_replay(replay)
    triage = triage_replay(replay, sentinel)
    gate = gate_actions(scenario, replay, sentinel, triage)
    ledger = build_evidence_ledger(scenario, replay, sentinel, triage, gate)
    queue = build_sync_queue(ledger)

    metrics = compute_metrics(scenario, replay, sentinel, triage, gate, ledger, queue)

    assert metrics.primary_cause_class == "timing_drift_or_stale_data"
    assert metrics.primary_cause_match is True
    assert metrics.hypothesis_separation > 0.0
    assert metrics.ledger_record_count > 0
    assert metrics.sync_envelope_count > 0
