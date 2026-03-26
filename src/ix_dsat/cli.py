from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from ix_dsat.claims import SCOPE, SYSTEM_NAME, SYSTEM_SHORT_NAME
from ix_dsat.errors import ScenarioValidationError
from ix_dsat.gate import gate_actions
from ix_dsat.ledger import build_evidence_ledger
from ix_dsat.metrics import compute_metrics
from ix_dsat.replay import replay_scenario
from ix_dsat.scenario import load_scenario
from ix_dsat.sentinel import scan_replay
from ix_dsat.sync_queue import build_sync_queue
from ix_dsat.triage import triage_replay
from ix_dsat.validation import validate_run
from ix_dsat.version import __version__


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ix-dsat",
        description=(
            "IX-Deep-Space-Anomaly-Triage: scope and scenario interface for a "
            "simulation-first onboard anomaly-triage scaffold."
        ),
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print the package version and exit.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the scope posture as JSON.",
    )
    parser.add_argument(
        "--validate-scenario",
        metavar="PATH",
        help="Validate a scenario JSON file against the DSAT contract.",
    )
    parser.add_argument(
        "--replay-scenario",
        metavar="PATH",
        help="Execute a deterministic replay for a validated scenario JSON file.",
    )
    parser.add_argument(
        "--sentinel-scan",
        metavar="PATH",
        help="Run the health sentinel over a deterministic replay for a scenario JSON file.",
    )
    parser.add_argument(
        "--triage-scan",
        metavar="PATH",
        help="Run replay, health sentinel, and bounded anomaly triage for a scenario JSON file.",
    )
    parser.add_argument(
        "--gate-scan",
        metavar="PATH",
        help="Run replay, health sentinel, triage, and safe-action gate for a scenario JSON file.",
    )
    parser.add_argument(
        "--ledger-scan",
        metavar="PATH",
        help="Run the full DSAT chain and emit a blackbox evidence ledger summary.",
    )
    parser.add_argument(
        "--sync-queue-scan",
        metavar="PATH",
        help="Run the full DSAT chain and emit a delay-tolerant sync queue summary.",
    )
    parser.add_argument(
        "--metrics-scan",
        metavar="PATH",
        help="Run the full DSAT chain and emit bounded validation metrics.",
    )
    parser.add_argument(
        "--validate-run",
        metavar="PATH",
        help="Run the full DSAT chain and emit an end-to-end pass/fail validation report.",
    )
    parser.add_argument(
        "--sample-every",
        metavar="N",
        type=int,
        default=1,
        help="For replay-derived scans, keep every Nth tick as a sample. Defaults to 1.",
    )
    return parser


def _run_full_chain(path: str, sample_every: int):
    scenario = load_scenario(path)
    replay = replay_scenario(scenario, sample_every_n_ticks=sample_every)
    sentinel = scan_replay(replay)
    triage = triage_replay(replay, sentinel)
    gate = gate_actions(scenario, replay, sentinel, triage)
    ledger = build_evidence_ledger(scenario, replay, sentinel, triage, gate)
    queue = build_sync_queue(ledger)
    metrics = compute_metrics(scenario, replay, sentinel, triage, gate, ledger, queue)
    validation = validate_run(metrics, gate, queue)
    return scenario, replay, sentinel, triage, gate, ledger, queue, metrics, validation


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(__version__)
        return 0

    if args.validate_scenario:
        try:
            scenario = load_scenario(args.validate_scenario)
        except ScenarioValidationError as exc:
            print(f"scenario validation failed: {exc}")
            return 2
        print(json.dumps(scenario.summary(), indent=2))
        return 0

    if args.replay_scenario:
        try:
            scenario = load_scenario(args.replay_scenario)
            result = replay_scenario(scenario, sample_every_n_ticks=args.sample_every)
        except ScenarioValidationError as exc:
            print(f"scenario replay failed: {exc}")
            return 2
        print(json.dumps(result.summary(), indent=2))
        return 0

    if args.sentinel_scan:
        try:
            scenario = load_scenario(args.sentinel_scan)
            result = replay_scenario(scenario, sample_every_n_ticks=args.sample_every)
            report = scan_replay(result)
        except ScenarioValidationError as exc:
            print(f"sentinel scan failed: {exc}")
            return 2
        print(json.dumps(report.summary(), indent=2))
        return 0

    if args.triage_scan:
        try:
            scenario = load_scenario(args.triage_scan)
            result = replay_scenario(scenario, sample_every_n_ticks=args.sample_every)
            sentinel = scan_replay(result)
            report = triage_replay(result, sentinel)
        except ScenarioValidationError as exc:
            print(f"triage scan failed: {exc}")
            return 2
        print(json.dumps(report.summary(), indent=2))
        return 0

    if args.gate_scan:
        try:
            _scenario, _replay, _sentinel, _triage, gate, _ledger, _queue, _metrics, _validation = _run_full_chain(
                args.gate_scan, args.sample_every
            )
        except ScenarioValidationError as exc:
            print(f"gate scan failed: {exc}")
            return 2
        print(json.dumps(gate.summary(), indent=2))
        return 0

    if args.ledger_scan:
        try:
            _scenario, _replay, _sentinel, _triage, _gate, ledger, _queue, _metrics, _validation = _run_full_chain(
                args.ledger_scan, args.sample_every
            )
        except ScenarioValidationError as exc:
            print(f"ledger scan failed: {exc}")
            return 2
        print(json.dumps(ledger.summary(), indent=2))
        return 0

    if args.sync_queue_scan:
        try:
            _scenario, _replay, _sentinel, _triage, _gate, _ledger, queue, _metrics, _validation = _run_full_chain(
                args.sync_queue_scan, args.sample_every
            )
        except ScenarioValidationError as exc:
            print(f"sync queue scan failed: {exc}")
            return 2
        print(json.dumps(queue.summary(), indent=2))
        return 0

    if args.metrics_scan:
        try:
            _scenario, _replay, _sentinel, _triage, _gate, _ledger, _queue, metrics, _validation = _run_full_chain(
                args.metrics_scan, args.sample_every
            )
        except ScenarioValidationError as exc:
            print(f"metrics scan failed: {exc}")
            return 2
        print(json.dumps(metrics.summary(), indent=2))
        return 0

    if args.validate_run:
        try:
            _scenario, _replay, _sentinel, _triage, _gate, _ledger, _queue, _metrics, validation = _run_full_chain(
                args.validate_run, args.sample_every
            )
        except ScenarioValidationError as exc:
            print(f"run validation failed: {exc}")
            return 2
        print(json.dumps(validation.summary(), indent=2))
        return 0

    payload = {
        "system_name": SYSTEM_NAME,
        "system_short_name": SYSTEM_SHORT_NAME,
        "version": __version__,
        "scope": asdict(SCOPE),
    }

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"{payload['system_name']} ({payload['system_short_name']})")
    print(f"version: {payload['version']}")
    print(f"mission: {payload['scope']['mission']}")
    print(f"first target: {payload['scope']['first_target']}")
    print("outputs:")
    for item in payload["scope"]["outputs"]:
        print(f"  - {item}")
    print("claims:")
    for item in payload["scope"]["claims"]:
        print(f"  - {item}")
    print("non-claims:")
    for item in payload["scope"]["non_claims"]:
        print(f"  - {item}")

    return 0
