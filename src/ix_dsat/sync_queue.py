from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Final

from ix_dsat.ledger import EvidenceLedger, LedgerRecord


PRIORITY_ORDER: Final[tuple[str, ...]] = ("critical", "high", "normal", "low")


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True, slots=True)
class SyncEnvelope:
    """
    One deterministic delay-tolerant sync envelope.
    """

    envelope_id: str
    sequence: int
    priority: str
    record_count: int
    first_record_index: int
    last_record_index: int
    manifest_hash: str
    records: tuple[LedgerRecord, ...]

    def to_dict(self) -> dict[str, Any]:
        """
        JSON-serializable envelope representation.
        """
        return {
            "envelope_id": self.envelope_id,
            "sequence": self.sequence,
            "priority": self.priority,
            "record_count": self.record_count,
            "first_record_index": self.first_record_index,
            "last_record_index": self.last_record_index,
            "manifest_hash": self.manifest_hash,
            "records": [record.to_dict() for record in self.records],
        }


@dataclass(frozen=True, slots=True)
class DelayTolerantSyncQueue:
    """
    Deterministic store-and-forward queue derived from the evidence ledger.
    """

    scenario_id: str
    chain_head: str
    envelope_count: int
    envelopes: tuple[SyncEnvelope, ...]

    def to_dict(self) -> dict[str, Any]:
        """
        JSON-serializable queue representation.
        """
        return {
            "scenario_id": self.scenario_id,
            "chain_head": self.chain_head,
            "envelope_count": self.envelope_count,
            "envelopes": [envelope.to_dict() for envelope in self.envelopes],
        }

    def summary(self) -> dict[str, Any]:
        """
        Compact summary suitable for CLI output.
        """
        return {
            "scenario_id": self.scenario_id,
            "chain_head": self.chain_head,
            "envelope_count": self.envelope_count,
            "priorities": [envelope.priority for envelope in self.envelopes],
            "record_counts": [envelope.record_count for envelope in self.envelopes],
            "manifest_hashes": [envelope.manifest_hash for envelope in self.envelopes],
        }


def _priority_for_record(record: LedgerRecord) -> str:
    if record.record_type in {
        "gate_report",
        "anomaly_detected",
        "triage_emitted",
        "confidence_degraded",
        "recovery_action_bounded",
    }:
        return "critical"
    if record.record_type in {
        "triage_report",
        "sentinel_report",
        "replay_summary",
        "comm_window_loss",
    }:
        return "high"
    if record.record_type in {
        "scenario_contract_snapshot",
        "line_confidence_assessed",
        "fault_effects_resolved",
        "scenario_started",
    }:
        return "normal"
    return "low"


def _manifest_hash(
    *,
    envelope_id: str,
    priority: str,
    records: tuple[LedgerRecord, ...],
) -> str:
    manifest = {
        "envelope_id": envelope_id,
        "priority": priority,
        "record_indices": [record.record_index for record in records],
        "record_hashes": [record.record_hash for record in records],
    }
    return hashlib.sha256(_canonical_json(manifest).encode("utf-8")).hexdigest()


def _chunk(records: list[LedgerRecord], size: int) -> list[tuple[LedgerRecord, ...]]:
    if size <= 0:
        size = 1
    return [tuple(records[index : index + size]) for index in range(0, len(records), size)]


def build_sync_queue(
    ledger: EvidenceLedger,
    *,
    max_records_per_envelope: int = 6,
) -> DelayTolerantSyncQueue:
    """
    Build a deterministic delay-tolerant sync queue from a blackbox ledger.
    """
    buckets: dict[str, list[LedgerRecord]] = {priority: [] for priority in PRIORITY_ORDER}
    for record in ledger.records:
        buckets[_priority_for_record(record)].append(record)

    envelopes: list[SyncEnvelope] = []
    sequence = 0

    for priority in PRIORITY_ORDER:
        for chunk in _chunk(buckets[priority], max_records_per_envelope):
            envelope_id = f"{ledger.scenario_id}-sync-{sequence:03d}"
            manifest_hash = _manifest_hash(
                envelope_id=envelope_id,
                priority=priority,
                records=chunk,
            )
            envelopes.append(
                SyncEnvelope(
                    envelope_id=envelope_id,
                    sequence=sequence,
                    priority=priority,
                    record_count=len(chunk),
                    first_record_index=chunk[0].record_index,
                    last_record_index=chunk[-1].record_index,
                    manifest_hash=manifest_hash,
                    records=chunk,
                )
            )
            sequence += 1

    return DelayTolerantSyncQueue(
        scenario_id=ledger.scenario_id,
        chain_head=ledger.chain_head,
        envelope_count=len(envelopes),
        envelopes=tuple(envelopes),
    )
