from ix_dsat.gate import gate_actions
from ix_dsat.ledger import build_evidence_ledger
from ix_dsat.replay import replay_scenario
from ix_dsat.scenario import load_scenario
from ix_dsat.sentinel import scan_replay
from ix_dsat.triage import triage_replay


def test_ledger_is_deterministic_and_chain_hashed() -> None:
    scenario = load_scenario("scenarios/examples/link_state_pointing_drift.json")
    replay = replay_scenario(scenario, sample_every_n_ticks=10)
    sentinel = scan_replay(replay)
    triage = triage_replay(replay, sentinel)
    gate = gate_actions(scenario, replay, sentinel, triage)

    ledger_a = build_evidence_ledger(scenario, replay, sentinel, triage, gate)
    ledger_b = build_evidence_ledger(scenario, replay, sentinel, triage, gate)

    assert ledger_a.chain_head == ledger_b.chain_head
    assert ledger_a.record_count == ledger_b.record_count
    assert ledger_a.records[0].previous_hash == "GENESIS"
    assert ledger_a.records[-1].record_hash == ledger_a.chain_head


def test_ledger_contains_core_reports() -> None:
    scenario = load_scenario("scenarios/examples/timing_bias_growth.json")
    replay = replay_scenario(scenario, sample_every_n_ticks=10)
    sentinel = scan_replay(replay)
    triage = triage_replay(replay, sentinel)
    gate = gate_actions(scenario, replay, sentinel, triage)
    ledger = build_evidence_ledger(scenario, replay, sentinel, triage, gate)

    record_types = [record.record_type for record in ledger.records]

    assert "scenario_contract_snapshot" in record_types
    assert "replay_summary" in record_types
    assert "sentinel_report" in record_types
    assert "triage_report" in record_types
    assert "gate_report" in record_types
    assert "anomaly_detected" in record_types
