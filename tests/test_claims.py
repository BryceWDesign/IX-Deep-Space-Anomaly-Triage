from ix_dsat.claims import SCOPE, SYSTEM_NAME, SYSTEM_SHORT_NAME


def test_system_identity() -> None:
    assert SYSTEM_NAME == "IX-Deep-Space-Anomaly-Triage"
    assert SYSTEM_SHORT_NAME == "DSAT"


def test_scope_is_deliberately_narrow() -> None:
    assert "delayed-ground" in SCOPE.mission
    assert "Communication and adjacent vehicle-state trust" in SCOPE.first_target


def test_non_claims_block_overreach() -> None:
    expected = {
        "Not a flight-qualified system.",
        "Not a certification package.",
        "Not a replacement for GN&C, comms, or full spacecraft FDIR.",
        "Not a claim of autonomous mission execution.",
        "Not a claim of guaranteed anomaly detection or fault isolation correctness.",
    }
    assert set(SCOPE.non_claims) == expected
