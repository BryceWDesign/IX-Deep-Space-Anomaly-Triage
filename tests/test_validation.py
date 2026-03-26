from ix_dsat.gate import gate_actions
from ix_dsat.ledger import build_evidence_ledger
from ix_dsat.metrics import compute_metrics
from ix_dsat.replay import replay_scenario
from ix_dsat.scenario import load_scenario
from ix_dsat.sentinel import scan_replay
from ix_dsat.sync_queue import build_sync_queue
from ix_dsat.triage import triage_replay
from ix_dsat.validation import validate_run


def test_validation_passes_link_state_scenario() -> None:
    scenario = load_scenario("scenarios/examples/link_state_pointing_drift.json")
    replay = replay_scenario(scenario, sample_every_n_ticks=10)
    sentinel = scan_replay(replay)
    triage = triage_replay(replay, sentinel)
    gate = gate_actions(scenario, replay, sentinel, triage)
    ledger = build_evidence_ledger(scenario, replay, sentinel, triage, gate)
    queue = build_sync_queue(ledger)
    metrics = compute_metrics(scenario, replay, sentinel, triage, gate, ledger, queue)

    report = validate_run(metrics, gate, queue)

    assert report.passed is True
    assert all(check.passed for check in report.checks)


def test_validation_passes_timing_scenario() -> None:
    scenario = load_scenario("scenarios/examples/timing_bias_growth.json")
    replay = replay_scenario(scenario, sample_every_n_ticks=10)
    sentinel = scan_replay(replay)
    triage = triage_replay(replay, sentinel)
    gate = gate_actions(scenario, replay, sentinel, triage)
    ledger = build_evidence_ledger(scenario, replay, sentinel, triage, gate)
    queue = build_sync_queue(ledger)
    metrics = compute_metrics(scenario, replay, sentinel, triage, gate, ledger, queue)

    report = validate_run(metrics, gate, queue)

    assert report.passed is True
    assert report.summary()["passed_check_count"] == len(report.checks)
