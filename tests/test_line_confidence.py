from ix_dsat.faults import FaultEffectAggregate
from ix_dsat.line_confidence import assess_line_confidence, build_inputs


def test_line_confidence_stays_nominal_under_clean_conditions() -> None:
    assessment = assess_line_confidence(
        build_inputs(
            baseline_confidence=0.96,
            pointing_error_deg=0.10,
            telemetry_freshness_s=0.40,
            clock_bias_ms=2.0,
            comm_window_open=True,
            effects=FaultEffectAggregate(),
        )
    )

    assert assessment.status == "nominal"
    assert assessment.confidence == 0.96
    assert assessment.dominant_factors == ("nominal_margin",)


def test_line_confidence_flags_pointing_and_dropout_pressure() -> None:
    assessment = assess_line_confidence(
        build_inputs(
            baseline_confidence=0.96,
            pointing_error_deg=3.2,
            telemetry_freshness_s=4.5,
            clock_bias_ms=12.0,
            comm_window_open=False,
            effects=FaultEffectAggregate(
                packet_loss_ratio=0.25,
                dropout_level=0.9,
            ),
        )
    )

    assert assessment.status == "critical"
    assert assessment.confidence < 0.35
    assert "dropout" in assessment.dominant_factors
    assert "pointing_error" in assessment.dominant_factors
