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
