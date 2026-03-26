from ix_dsat.faults import FaultEffectAggregate, resolve_fault_effects
from ix_dsat.scenario import load_scenario


def test_fault_library_resolves_pointing_drift_and_packet_loss() -> None:
    scenario = load_scenario("scenarios/examples/link_state_pointing_drift.json")
    active_faults = tuple(scenario.faults[:2])

    effects, observations = resolve_fault_effects(active_faults)

    assert round(effects.pointing_drift_deg_per_s, 6) == round(0.045 * 0.67, 6)
    assert round(effects.packet_loss_ratio, 6) == round(0.22 * 0.55, 6)
    assert len(observations) == 2
    assert {obs.fault_type for obs in observations} == {"pointing_drift", "packet_loss"}


def test_fault_library_combines_bounds_conservatively() -> None:
    left = FaultEffectAggregate(
        packet_loss_ratio=0.20,
        sensor_bias_level=0.40,
        stale_growth_s_per_s=1.5,
    )
    right = FaultEffectAggregate(
        packet_loss_ratio=0.10,
        sensor_bias_level=0.75,
        stale_growth_s_per_s=2.0,
        mode_mismatch_level=0.33,
    )

    combined = left.combine(right)

    assert combined.packet_loss_ratio == 0.20
    assert combined.sensor_bias_level == 0.75
    assert combined.stale_growth_s_per_s == 3.5
    assert combined.mode_mismatch_level == 0.33


def test_fault_library_resolves_timing_bias_scenario() -> None:
    scenario = load_scenario("scenarios/examples/timing_bias_growth.json")
    effects, observations = resolve_fault_effects(scenario.faults)

    assert effects.clock_bias_growth_ms_per_s > 0.0
    assert effects.stale_growth_s_per_s > 0.0
    assert any(obs.fault_type == "clock_bias_growth" for obs in observations)
    assert any(obs.fault_type == "sensor_stale" for obs in observations)
