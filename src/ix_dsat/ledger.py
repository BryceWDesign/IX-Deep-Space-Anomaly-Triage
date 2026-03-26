from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

from ix_dsat.gate import GateReport
from ix_dsat.replay import ReplayEvent, ReplayResult
from ix_dsat.scenario import Scenario
from ix_dsat.sentinel import SentinelReport
from ix_dsat.triage import TriageReport


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _record_hash(
    *,
    record_index: int,
    record_type: str,
    time_s: float | None,
    previous_hash: str,
    payload: dict[str, Any],
) -> str:
    material = {
        "record_index": record_index,
        "record_type": record_type,
        "time_s": time_s,
        "previous_hash": previous_hash,
        "payload": payload,
    }
    encoded = _canonical_json(material).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class LedgerRecord:
    """
    One append-only evidence record.
    """

    record_index: int
    record_type: str
    time_s: float | None
    previous_hash: str
    record_hash: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """
        JSON-serializable record representation.
        """
        return {
            "record_index": self.record_index,
            "record_type": self.record_type,
            "time_s": self.time_s,
            "previous_hash": self.previous_hash,
            "record_hash": self.record_hash,
            "payload": self.payload,
        }


@dataclass(frozen=True, slots=True)
class EvidenceLedger:
    """
    Append-only blackbox evidence ledger.
    """

    scenario_id: str
    chain_head: str
    record_count: int
    records: tuple[LedgerRecord, ...]

    def to_dict(self) -> dict[str, Any]:
        """
        JSON-serializable ledger representation.
        """
        return {
            "scenario_id": self.scenario_id,
            "chain_head": self.chain_head,
            "record_count": self.record_count,
            "records": [record.to_dict() for record in self.records],
        }

    def summary(self) -> dict[str, Any]:
        """
        Compact summary suitable for CLI output.
        """
        return {
            "scenario_id": self.scenario_id,
            "chain_head": self.chain_head,
            "record_count": self.record_count,
            "record_types": [record.record_type for record in self.records],
            "first_record_time_s": self.records[0].time_s if self.records else None,
            "last_record_time_s": self.records[-1].time_s if self.records else None,
        }


def _append_record(
    records: list[LedgerRecord],
    *,
    record_type: str,
    time_s: float | None,
    payload: dict[str, Any],
) -> None:
    previous_hash = records[-1].record_hash if records else "GENESIS"
    record_index = len(records)
    record_hash = _record_hash(
        record_index=record_index,
        record_type=record_type,
        time_s=time_s,
        previous_hash=previous_hash,
        payload=payload,
    )
    records.append(
        LedgerRecord(
            record_index=record_index,
            record_type=record_type,
            time_s=time_s,
            previous_hash=previous_hash,
            record_hash=record_hash,
            payload=payload,
        )
    )


def _scenario_snapshot_payload(scenario: Scenario) -> dict[str, Any]:
    return {
        "schema_version": scenario.schema_version,
        "scenario_id": scenario.scenario_id,
        "title": scenario.title,
        "description": scenario.description,
        "metadata": asdict(scenario.metadata),
        "timeline": asdict(scenario.timeline),
        "initial_state": asdict(scenario.initial_state),
        "telemetry_channel_count": len(scenario.telemetry_channels),
        "fault_count": len(scenario.faults),
        "expected": asdict(scenario.expected),
    }


def _replay_event_payload(event: ReplayEvent) -> dict[str, Any]:
    return {
        "event_type": event.event_type,
        "severity": event.severity,
        "message": event.message,
        "details": event.details,
    }


def build_evidence_ledger(
    scenario: Scenario,
    replay: ReplayResult,
    sentinel: SentinelReport,
    triage: TriageReport,
    gate: GateReport,
) -> EvidenceLedger:
    """
    Build a deterministic append-only ledger for a DSAT scenario execution.
    """
    records: list[LedgerRecord] = []

    _append_record(
        records,
        record_type="scenario_contract_snapshot",
        time_s=0.0,
        payload=_scenario_snapshot_payload(scenario),
    )
    _append_record(
        records,
        record_type="replay_summary",
        time_s=replay.first_anomaly_time_s,
        payload=replay.summary(),
    )

    for event in replay.events:
        _append_record(
            records,
            record_type=event.event_type,
            time_s=event.time_s,
            payload=_replay_event_payload(event),
        )

    _append_record(
        records,
        record_type="sentinel_report",
        time_s=replay.first_anomaly_time_s,
        payload=sentinel.to_dict(),
    )
    _append_record(
        records,
        record_type="triage_report",
        time_s=replay.first_anomaly_time_s,
        payload=triage.to_dict(),
    )
    _append_record(
        records,
        record_type="gate_report",
        time_s=replay.first_anomaly_time_s,
        payload=gate.to_dict(),
    )

    chain_head = records[-1].record_hash if records else "GENESIS"
    return EvidenceLedger(
        scenario_id=scenario.scenario_id,
        chain_head=chain_head,
        record_count=len(records),
        records=tuple(records),
    )
