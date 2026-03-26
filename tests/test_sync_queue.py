from ix_dsat.gate import gate_actions
from ix_dsat.ledger import build_evidence_ledger
from ix_dsat.replay import replay_scenario
from ix_dsat.scenario import load_scenario
from ix_dsat.sentinel import scan_replay
from ix_dsat.sync_queue import build_sync_queue
from ix_dsat.triage import triage_replay


def test_sync_queue_is_deterministic() -> None:
    scenario = load_scenario("scenarios/examples/link_state_pointing_drift.json")
    replay = replay_scenario(scenario, sample_every_n_ticks=10)
    sentinel = scan_replay(replay)
    triage = triage_replay(replay, sentinel)
    gate = gate_actions(scenario, replay, sentinel, triage)
    ledger = build_evidence_ledger(scenario, replay, sentinel, triage, gate)

    queue_a = build_sync_queue(ledger, max_records_per_envelope=4)
    queue_b = build_sync_queue(ledger, max_records_per_envelope=4)

    assert queue_a.summary() == queue_b.summary()


def test_sync_queue_prioritizes_critical_records_first() -> None:
    scenario = load_scenario("scenarios/examples/link_state_pointing_drift.json")
    replay = replay_scenario(scenario, sample_every_n_ticks=10)
    sentinel = scan_replay(replay)
    triage = triage_replay(replay, sentinel)
    gate = gate_actions(scenario, replay, sentinel, triage)
    ledger = build_evidence_ledger(scenario, replay, sentinel, triage, gate)
    queue = build_sync_queue(ledger, max_records_per_envelope=3)

    assert queue.envelopes
    assert queue.envelopes[0].priority == "critical"
    first_types = [record.record_type for record in queue.envelopes[0].records]
    assert any(
        record_type in {"anomaly_detected", "triage_emitted", "gate_report", "confidence_degraded"}
        for record_type in first_types
    )


def test_sync_queue_manifest_hashes_exist() -> None:
    scenario = load_scenario("scenarios/examples/timing_bias_growth.json")
    replay = replay_scenario(scenario, sample_every_n_ticks=10)
    sentinel = scan_replay(replay)
    triage = triage_replay(replay, sentinel)
    gate = gate_actions(scenario, replay, sentinel, triage)
    ledger = build_evidence_ledger(scenario, replay, sentinel, triage, gate)
    queue = build_sync_queue(ledger)

    assert queue.envelope_count == len(queue.envelopes)
    assert all(envelope.manifest_hash for envelope in queue.envelopes)
    assert queue.chain_head == ledger.chain_head
