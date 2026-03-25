from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from ix_dsat.claims import SCOPE, SYSTEM_NAME, SYSTEM_SHORT_NAME
from ix_dsat.errors import ScenarioValidationError
from ix_dsat.replay import replay_scenario
from ix_dsat.scenario import load_scenario
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
        "--sample-every",
        metavar="N",
        type=int,
        default=1,
        help="For replay, keep every Nth tick as a sample. Defaults to 1.",
    )
    return parser


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
