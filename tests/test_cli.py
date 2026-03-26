from pathlib import Path

from ix_dsat.cli import main


def test_cli_version(capsys) -> None:
    rc = main(["--version"])
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out.strip() == "0.1.0"


def test_cli_json(capsys) -> None:
    rc = main(["--json"])
    captured = capsys.readouterr()
    assert rc == 0
    assert '"system_name": "IX-Deep-Space-Anomaly-Triage"' in captured.out
    assert '"system_short_name": "DSAT"' in captured.out
    assert '"mission"' in captured.out


def test_cli_validate_scenario(capsys) -> None:
    scenario_path = Path("scenarios/examples/link_state_pointing_drift.json")
    rc = main(["--validate-scenario", str(scenario_path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert '"scenario_id": "comm-link-pointing-drift-001"' in captured.out
    assert '"expected_cause_class": "link_state_degradation"' in captured.out


def test_cli_replay_scenario(capsys) -> None:
    scenario_path = Path("scenarios/examples/link_state_pointing_drift.json")
    rc = main(["--replay-scenario", str(scenario_path), "--sample-every", "10"])
    captured = capsys.readouterr()
    assert rc == 0
    assert '"scenario_id": "comm-link-pointing-drift-001"' in captured.out
    assert '"anomaly_detected": true' in captured.out
    assert '"cause_class_hint": "link_state_degradation"' in captured.out


def test_cli_sentinel_scan(capsys) -> None:
    scenario_path = Path("scenarios/examples/link_state_pointing_drift.json")
    rc = main(["--sentinel-scan", str(scenario_path), "--sample-every", "10"])
    captured = capsys.readouterr()
    assert rc == 0
    assert '"scenario_id": "comm-link-pointing-drift-001"' in captured.out
    assert '"overall_status": "critical"' in captured.out
    assert '"recommended_posture": "enter_bounded_recovery_only"' in captured.out


def test_cli_triage_scan(capsys) -> None:
    scenario_path = Path("scenarios/examples/timing_bias_growth.json")
    rc = main(["--triage-scan", str(scenario_path), "--sample-every", "10"])
    captured = capsys.readouterr()
    assert rc == 0
    assert '"scenario_id": "comm-timing-bias-growth-001"' in captured.out
    assert '"primary_cause_class": "timing_drift_or_stale_data"' in captured.out
