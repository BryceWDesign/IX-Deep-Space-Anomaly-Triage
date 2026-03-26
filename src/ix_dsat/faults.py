from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ix_dsat.scenario import FaultInjection


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


@dataclass(frozen=True, slots=True)
class FaultEffectAggregate:
    """
    Deterministic aggregate of seeded fault effects for one replay step.
    """

    packet_loss_ratio: float = 0.0
    sensor_bias_level: float = 0.0
    mode_mismatch_level: float = 0.0
    dropout_level: float = 0.0
    stale_growth_s_per_s: float = 0.0
    pointing_drift_deg_per_s: float = 0.0
    clock_bias_growth_ms_per_s: float = 0.0

    def combine(self, other: "FaultEffectAggregate") -> "FaultEffectAggregate":
        """
        Combine two effect aggregates using conservative, bounded rules.
        """
        return FaultEffectAggregate(
            packet_loss_ratio=max(self.packet_loss_ratio, other.packet_loss_ratio),
            sensor_bias_level=max(self.sensor_bias_level, other.sensor_bias_level),
            mode_mismatch_level=max(self.mode_mismatch_level, other.mode_mismatch_level),
            dropout_level=max(self.dropout_level, other.dropout_level),
            stale_growth_s_per_s=self.stale_growth_s_per_s + other.stale_growth_s_per_s,
            pointing_drift_deg_per_s=self.pointing_drift_deg_per_s
            + other.pointing_drift_deg_per_s,
            clock_bias_growth_ms_per_s=self.clock_bias_growth_ms_per_s
            + other.clock_bias_growth_ms_per_s,
        )

    def to_dict(self) -> dict[str, float]:
        """
        Return a plain dictionary representation.
        """
        return {
            "packet_loss_ratio": self.packet_loss_ratio,
            "sensor_bias_level": self.sensor_bias_level,
            "mode_mismatch_level": self.mode_mismatch_level,
            "dropout_level": self.dropout_level,
            "stale_growth_s_per_s": self.stale_growth_s_per_s,
            "pointing_drift_deg_per_s": self.pointing_drift_deg_per_s,
            "clock_bias_growth_ms_per_s": self.clock_bias_growth_ms_per_s,
        }


@dataclass(frozen=True, slots=True)
class FaultObservation:
    """
    One deterministic observation emitted by the fault library.
    """

    fault_id: str
    fault_type: str
    target: str
    severity: float
    message: str
    derived: dict[str, float | str]


FaultHandler = Callable[[FaultInjection], tuple[FaultEffectAggregate, FaultObservation]]


def _handle_pointing_drift(fault: FaultInjection) -> tuple[FaultEffectAggregate, FaultObservation]:
    base_rate = float(fault.parameters.get("drift_rate_deg_per_s", 0.0))
    onset_profile = str(fault.parameters.get("onset_profile", "step"))
    effective_rate = _clamp(base_rate * fault.severity, 0.0, 10.0)
    effect = FaultEffectAggregate(pointing_drift_deg_per_s=effective_rate)
    observation = FaultObservation(
        fault_id=fault.fault_id,
        fault_type=fault.fault_type,
        target=fault.target,
        severity=fault.severity,
        message="Pointing drift fault active.",
        derived={
            "effective_drift_deg_per_s": effective_rate,
            "onset_profile": onset_profile,
        },
    )
    return effect, observation


def _handle_packet_loss(fault: FaultInjection) -> tuple[FaultEffectAggregate, FaultObservation]:
    base_loss_ratio = float(fault.parameters.get("loss_ratio", 0.0))
    burst_length_packets = float(fault.parameters.get("burst_length_packets", 0.0))
    effective_loss_ratio = _clamp(base_loss_ratio * fault.severity, 0.0, 1.0)
    effect = FaultEffectAggregate(packet_loss_ratio=effective_loss_ratio)
    observation = FaultObservation(
        fault_id=fault.fault_id,
        fault_type=fault.fault_type,
        target=fault.target,
        severity=fault.severity,
        message="Packet-loss fault active.",
        derived={
            "effective_loss_ratio": effective_loss_ratio,
            "burst_length_packets": burst_length_packets,
        },
    )
    return effect, observation


def _handle_sensor_stale(fault: FaultInjection) -> tuple[FaultEffectAggregate, FaultObservation]:
    growth = float(fault.parameters.get("age_growth_s_per_s", 0.0))
    effective_growth = _clamp(growth * fault.severity, 0.0, 60.0)
    effect = FaultEffectAggregate(stale_growth_s_per_s=effective_growth)
    observation = FaultObservation(
        fault_id=fault.fault_id,
        fault_type=fault.fault_type,
        target=fault.target,
        severity=fault.severity,
        message="Sensor-staleness fault active.",
        derived={"effective_age_growth_s_per_s": effective_growth},
    )
    return effect, observation


def _handle_clock_bias_growth(
    fault: FaultInjection,
) -> tuple[FaultEffectAggregate, FaultObservation]:
    growth = float(fault.parameters.get("bias_growth_ms_per_s", 0.0))
    effective_growth = _clamp(growth * fault.severity, 0.0, 5000.0)
    effect = FaultEffectAggregate(clock_bias_growth_ms_per_s=effective_growth)
    observation = FaultObservation(
        fault_id=fault.fault_id,
        fault_type=fault.fault_type,
        target=fault.target,
        severity=fault.severity,
        message="Clock-bias growth fault active.",
        derived={"effective_bias_growth_ms_per_s": effective_growth},
    )
    return effect, observation


def _handle_sensor_bias(fault: FaultInjection) -> tuple[FaultEffectAggregate, FaultObservation]:
    declared_bias = float(fault.parameters.get("bias_level", fault.severity))
    effective_bias = _clamp(max(declared_bias, fault.severity), 0.0, 1.0)
    effect = FaultEffectAggregate(sensor_bias_level=effective_bias)
    observation = FaultObservation(
        fault_id=fault.fault_id,
        fault_type=fault.fault_type,
        target=fault.target,
        severity=fault.severity,
        message="Sensor-bias fault active.",
        derived={"effective_bias_level": effective_bias},
    )
    return effect, observation


def _handle_dropout(fault: FaultInjection) -> tuple[FaultEffectAggregate, FaultObservation]:
    declared_level = float(fault.parameters.get("dropout_level", fault.severity))
    effective_level = _clamp(max(declared_level, fault.severity), 0.0, 1.0)
    effect = FaultEffectAggregate(dropout_level=effective_level)
    observation = FaultObservation(
        fault_id=fault.fault_id,
        fault_type=fault.fault_type,
        target=fault.target,
        severity=fault.severity,
        message="Dropout fault active.",
        derived={"effective_dropout_level": effective_level},
    )
    return effect, observation


def _handle_mode_mismatch(fault: FaultInjection) -> tuple[FaultEffectAggregate, FaultObservation]:
    mismatch_score = float(fault.parameters.get("mismatch_score", fault.severity))
    expected_mode = str(fault.parameters.get("expected_mode", "unknown"))
    observed_mode = str(fault.parameters.get("observed_mode", "unknown"))
    effective_score = _clamp(max(mismatch_score, fault.severity), 0.0, 1.0)
    effect = FaultEffectAggregate(mode_mismatch_level=effective_score)
    observation = FaultObservation(
        fault_id=fault.fault_id,
        fault_type=fault.fault_type,
        target=fault.target,
        severity=fault.severity,
        message="Mode-mismatch fault active.",
        derived={
            "effective_mismatch_score": effective_score,
            "expected_mode": expected_mode,
            "observed_mode": observed_mode,
        },
    )
    return effect, observation


FAULT_LIBRARY: dict[str, FaultHandler] = {
    "pointing_drift": _handle_pointing_drift,
    "packet_loss": _handle_packet_loss,
    "sensor_stale": _handle_sensor_stale,
    "clock_bias_growth": _handle_clock_bias_growth,
    "sensor_bias": _handle_sensor_bias,
    "dropout": _handle_dropout,
    "mode_mismatch": _handle_mode_mismatch,
}


def resolve_fault_effects(
    active_faults: tuple[FaultInjection, ...],
) -> tuple[FaultEffectAggregate, tuple[FaultObservation, ...]]:
    """
    Resolve active seeded faults into one bounded effect aggregate and a set of
    deterministic observations.

    Unknown fault types are ignored here on purpose because scenario validation
    should already reject them.
    """
    aggregate = FaultEffectAggregate()
    observations: list[FaultObservation] = []

    for fault in active_faults:
        handler = FAULT_LIBRARY.get(fault.fault_type)
        if handler is None:
            continue
        effect, observation = handler(fault)
        aggregate = aggregate.combine(effect)
        observations.append(observation)

    return aggregate, tuple(observations)
