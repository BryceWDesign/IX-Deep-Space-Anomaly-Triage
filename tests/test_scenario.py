import json
from pathlib import Path

import pytest

from ix_dsat.errors import ScenarioValidationError
from ix_dsat.scenario import load_scenario, scenario_from_dict


def test_load_example_scenario() -> None:
    scenario = load_scenario("scenarios/examples/link_state_pointing_drift.json")
    assert scenario.scenario_id == "comm-link-pointing-drift-001"
    assert scenario.expected.cause_class == "link_state_degradation"
    assert len(scenario.telemetry_channels) == 5
    assert len(scenario.faults) == 3


def test_duplicate_telemetry_channel_rejected() -> None:
    payload = json.loads(Path("scenarios/examples/link_state_pointing_drift.json").read_text())
    payload["telemetry_channels"].append(
        {
            "name": "line_confidence",
            "kind": "scalar",
            "units": "ratio",
            "nominal_min": 0.0,
            "nominal_max": 1.0,
            "initial_value": 0.95
        }
    )

    with pytest.raises(ScenarioValidationError, match="duplicate telemetry channel name"):
        scenario_from_dict(payload)


def test_action_sets_must_be_disjoint() -> None:
    payload = json.loads(Path("scenarios/examples/link_state_pointing_drift.json").read_text())
    payload["expected"]["blocked_actions"] = [
        "request_reacquisition",
        "enter_safe_comm_posture"
    ]

    with pytest.raises(ScenarioValidationError, match="must be disjoint"):
        scenario_from_dict(payload)


def test_fault_must_fit_timeline() -> None:
    payload = json.loads(Path("scenarios/examples/link_state_pointing_drift.json").read_text())
    payload["faults"][0]["end_s"] = 9999.0

    with pytest.raises(ScenarioValidationError, match="must be within scenario duration"):
        scenario_from_dict(payload)


def test_required_events_must_exist() -> None:
    payload = json.loads(Path("scenarios/examples/link_state_pointing_drift.json").read_text())
    payload["expected"]["must_emit_events"] = ["anomaly_detected"]

    with pytest.raises(ScenarioValidationError, match="must include required event"):
        scenario_from_dict(payload)
