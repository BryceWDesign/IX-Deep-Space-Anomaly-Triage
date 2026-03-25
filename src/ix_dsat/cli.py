from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from ix_dsat.claims import SCOPE, SYSTEM_NAME, SYSTEM_SHORT_NAME
from ix_dsat.version import __version__


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ix-dsat",
        description=(
            "IX-Deep-Space-Anomaly-Triage: scope and claims interface for a "
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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(__version__)
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
