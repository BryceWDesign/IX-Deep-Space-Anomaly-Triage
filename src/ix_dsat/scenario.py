from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ix_dsat.contracts import (
    ALLOWED_ACTIONS,
    ALLOWED_CAUSE_CLASSES,
    ALLOWED_FAULT_TYPES,
    ALLOWED_TELEMETRY_KINDS,
    CLOCK_BIAS_BOUNDS,
    LINE_CONFIDENCE_BOUNDS,
    POINTING_ERROR_BOUNDS,
    REQUIRED_EVENT_TYPES,
    SEVERITY_BOUNDS,
    TELEMETRY_FRESHNESS_BOUNDS,
)
from ix_dsat.errors import ScenarioValidationError


def _require_keys(mapping: dict[str, Any], keys: tuple[str, ...], context: str) -> None:
    missing = [key for key in keys if key not in mapping]
    if missing:
        raise ScenarioValidationError(f"{context} missing required keys: {', '.join(missing)}")


def _require_non_empty_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ScenarioValidationError(f"{field_name} must be a non-empty string")
    return value.strip()


def _require_number(value: Any, field_name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ScenarioValidationError(f"{field_name} must be a number")
    return float(value)


def _require_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ScenarioValidationError(f"{field_name} must be a boolean")
    return value


def _require_in_set(value: str, allowed: tuple[str, ...], field_name: str) -> str:
    if value not in allowed:
        joined = ", ".join(allowed)
        raise ScenarioValidationError(f"{field_name} must be one of: {joined}")
    return value


def _require_bounds(value: float, minimum: float, maximum: float, field_name: str) -> float:
    if value < minimum or value > maximum:
        raise ScenarioValidationError(
            f"{field_name} must be within [{minimum}, {maximum}], got {value}"
        )
    return value


@dataclass(frozen=True, slots=True)
class ScenarioMetadata:
    """
    Top-level metadata for a deterministic scenario.
    """

    domain: str
    subsystem: str
    author: str
    tags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ScenarioTimeline:
    """
    Timing contract for a scenario run.
    """

    duration_s: int
    tick_hz: int


@dataclass(frozen=True, slots=True)
class InitialState:
    """
    Starting system state before any seeded faults are applied.
    """

    comm_window_open: bool
    line_confidence: float
    vehicle_mode: str
    telemetry_freshness_s: float
    pointing_error_deg: float
    clock_bias_ms: float


@dataclass(frozen=True, slots=True)
class TelemetryChannel:
    """
    Telemetry channel definition.
    """

    name: str
    kind: str
    units: str
    nominal_min: float
    nominal_max: float
    initial_value: str | float | bool


@dataclass(frozen=True, slots=True)
class FaultInjection:
    """
    Seeded fault definition.
    """

    fault_id: str
    fault_type: str
    start_s: float
    end_s: float | None
    target: str
    severity: float
    parameters: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ExpectedBehavior:
    """
    Expected triage behavior for a scenario.
    """

    cause_class: str
    minimum_confidence_floor: float
    allowed_actions: tuple[str, ...]
    blocked_actions: tuple[str, ...]
    must_emit_events: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Scenario:
    """
    Full deterministic scenario contract.
    """

    schema_version: str
    scenario_id: str
    title: str
    description: str
    metadata: ScenarioMetadata
    timeline: ScenarioTimeline
    initial_state: InitialState
    telemetry_channels: tuple[TelemetryChannel, ...]
    faults: tuple[FaultInjection, ...]
    expected: ExpectedBehavior

    def to_dict(self) -> dict[str, Any]:
        """
        Return a plain-JSON representation of the scenario.
        """
        return asdict(self)

    def summary(self) -> dict[str, Any]:
        """
        Return a compact summary suitable for CLI output and test artifacts.
        """
        return {
            "schema_version": self.schema_version,
            "scenario_id": self.scenario_id,
            "title": self.title,
            "fault_count": len(self.faults),
            "telemetry_channel_count": len(self.telemetry_channels),
            "expected_cause_class": self.expected.cause_class,
            "allowed_actions": list(self.expected.allowed_actions),
            "blocked_actions": list(self.expected.blocked_actions),
        }


def _parse_metadata(payload: dict[str, Any]) -> ScenarioMetadata:
    _require_keys(payload, ("domain", "subsystem", "author", "tags"), "metadata")
    tags = payload["tags"]
    if not isinstance(tags, list) or not tags:
        raise ScenarioValidationError("metadata.tags must be a non-empty list of strings")
    normalized_tags = tuple(_require_non_empty_string(tag, "metadata.tags[]") for tag in tags)
    return ScenarioMetadata(
        domain=_require_non_empty_string(payload["domain"], "metadata.domain"),
        subsystem=_require_non_empty_string(payload["subsystem"], "metadata.subsystem"),
        author=_require_non_empty_string(payload["author"], "metadata.author"),
        tags=normalized_tags,
    )


def _parse_timeline(payload: dict[str, Any]) -> ScenarioTimeline:
    _require_keys(payload, ("duration_s", "tick_hz"), "timeline")
    duration_s = int(_require_number(payload["duration_s"], "timeline.duration_s"))
    tick_hz = int(_require_number(payload["tick_hz"], "timeline.tick_hz"))
    if duration_s <= 0:
        raise ScenarioValidationError("timeline.duration_s must be > 0")
    if tick_hz <= 0:
        raise ScenarioValidationError("timeline.tick_hz must be > 0")
    return ScenarioTimeline(duration_s=duration_s, tick_hz=tick_hz)


def _parse_initial_state(payload: dict[str, Any]) -> InitialState:
    _require_keys(
        payload,
        (
            "comm_window_open",
            "line_confidence",
            "vehicle_mode",
            "telemetry_freshness_s",
            "pointing_error_deg",
            "clock_bias_ms",
        ),
        "initial_state",
    )

    line_confidence = _require_bounds(
        _require_number(payload["line_confidence"], "initial_state.line_confidence"),
        LINE_CONFIDENCE_BOUNDS.minimum,
        LINE_CONFIDENCE_BOUNDS.maximum,
        "initial_state.line_confidence",
    )
    telemetry_freshness_s = _require_bounds(
        _require_number(
            payload["telemetry_freshness_s"], "initial_state.telemetry_freshness_s"
        ),
        TELEMETRY_FRESHNESS_BOUNDS.minimum,
        TELEMETRY_FRESHNESS_BOUNDS.maximum,
        "initial_state.telemetry_freshness_s",
    )
    pointing_error_deg = _require_bounds(
        _require_number(payload["pointing_error_deg"], "initial_state.pointing_error_deg"),
        POINTING_ERROR_BOUNDS.minimum,
        POINTING_ERROR_BOUNDS.maximum,
        "initial_state.pointing_error_deg",
    )
    clock_bias_ms = _require_bounds(
        _require_number(payload["clock_bias_ms"], "initial_state.clock_bias_ms"),
        CLOCK_BIAS_BOUNDS.minimum,
        CLOCK_BIAS_BOUNDS.maximum,
        "initial_state.clock_bias_ms",
    )

    return InitialState(
        comm_window_open=_require_bool(
            payload["comm_window_open"], "initial_state.comm_window_open"
        ),
        line_confidence=line_confidence,
        vehicle_mode=_require_non_empty_string(payload["vehicle_mode"], "initial_state.vehicle_mode"),
        telemetry_freshness_s=telemetry_freshness_s,
        pointing_error_deg=pointing_error_deg,
        clock_bias_ms=clock_bias_ms,
    )


def _parse_telemetry_channels(payload: list[dict[str, Any]]) -> tuple[TelemetryChannel, ...]:
    if not isinstance(payload, list) or not payload:
        raise ScenarioValidationError("telemetry_channels must be a non-empty list")

    channels: list[TelemetryChannel] = []
    names_seen: set[str] = set()

    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ScenarioValidationError(f"telemetry_channels[{index}] must be an object")

        _require_keys(
            item,
            ("name", "kind", "units", "nominal_min", "nominal_max", "initial_value"),
            f"telemetry_channels[{index}]",
        )

        name = _require_non_empty_string(item["name"], f"telemetry_channels[{index}].name")
        if name in names_seen:
            raise ScenarioValidationError(f"duplicate telemetry channel name: {name}")
        names_seen.add(name)

        kind = _require_in_set(
            _require_non_empty_string(item["kind"], f"telemetry_channels[{index}].kind"),
            ALLOWED_TELEMETRY_KINDS,
            f"telemetry_channels[{index}].kind",
        )
        units = _require_non_empty_string(item["units"], f"telemetry_channels[{index}].units")
        nominal_min = _require_number(
            item["nominal_min"], f"telemetry_channels[{index}].nominal_min"
        )
        nominal_max = _require_number(
            item["nominal_max"], f"telemetry_channels[{index}].nominal_max"
        )
        if nominal_min > nominal_max:
            raise ScenarioValidationError(
                f"telemetry_channels[{index}] nominal_min must be <= nominal_max"
            )

        initial_value = item["initial_value"]
        if kind == "scalar":
            initial_value = _require_number(
                initial_value, f"telemetry_channels[{index}].initial_value"
            )
            if initial_value < nominal_min or initial_value > nominal_max:
                raise ScenarioValidationError(
                    f"telemetry_channels[{index}].initial_value must be within nominal bounds"
                )
        elif kind == "boolean":
            initial_value = _require_bool(
                initial_value, f"telemetry_channels[{index}].initial_value"
            )
        else:
            initial_value = _require_non_empty_string(
                initial_value, f"telemetry_channels[{index}].initial_value"
            )

        channels.append(
            TelemetryChannel(
                name=name,
                kind=kind,
                units=units,
                nominal_min=nominal_min,
                nominal_max=nominal_max,
                initial_value=initial_value,
            )
        )

    return tuple(channels)


def _parse_faults(
    payload: list[dict[str, Any]], scenario_duration_s: int
) -> tuple[FaultInjection, ...]:
    if not isinstance(payload, list):
        raise ScenarioValidationError("faults must be a list")

    fault_ids: set[str] = set()
    faults: list[FaultInjection] = []

    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ScenarioValidationError(f"faults[{index}] must be an object")

        _require_keys(
            item,
            ("fault_id", "fault_type", "start_s", "target", "severity", "parameters"),
            f"faults[{index}]",
        )

        fault_id = _require_non_empty_string(item["fault_id"], f"faults[{index}].fault_id")
        if fault_id in fault_ids:
            raise ScenarioValidationError(f"duplicate fault_id: {fault_id}")
        fault_ids.add(fault_id)

        fault_type = _require_in_set(
            _require_non_empty_string(item["fault_type"], f"faults[{index}].fault_type"),
            ALLOWED_FAULT_TYPES,
            f"faults[{index}].fault_type",
        )
        start_s = _require_number(item["start_s"], f"faults[{index}].start_s")
        end_raw = item.get("end_s")
        end_s = None if end_raw is None else _require_number(end_raw, f"faults[{index}].end_s")
        target = _require_non_empty_string(item["target"], f"faults[{index}].target")
        severity = _require_bounds(
            _require_number(item["severity"], f"faults[{index}].severity"),
            SEVERITY_BOUNDS.minimum,
            SEVERITY_BOUNDS.maximum,
            f"faults[{index}].severity",
        )
        parameters = item["parameters"]
        if not isinstance(parameters, dict):
            raise ScenarioValidationError(f"faults[{index}].parameters must be an object")

        if start_s < 0.0 or start_s > float(scenario_duration_s):
            raise ScenarioValidationError(
                f"faults[{index}].start_s must be within scenario duration"
            )
        if end_s is not None:
            if end_s < start_s:
                raise ScenarioValidationError(f"faults[{index}].end_s must be >= start_s")
            if end_s > float(scenario_duration_s):
                raise ScenarioValidationError(
                    f"faults[{index}].end_s must be within scenario duration"
                )

        faults.append(
            FaultInjection(
                fault_id=fault_id,
                fault_type=fault_type,
                start_s=start_s,
                end_s=end_s,
                target=target,
                severity=severity,
                parameters=parameters,
            )
        )

    return tuple(faults)


def _parse_expected(payload: dict[str, Any]) -> ExpectedBehavior:
    _require_keys(
        payload,
        (
            "cause_class",
            "minimum_confidence_floor",
            "allowed_actions",
            "blocked_actions",
            "must_emit_events",
        ),
        "expected",
    )

    cause_class = _require_in_set(
        _require_non_empty_string(payload["cause_class"], "expected.cause_class"),
        ALLOWED_CAUSE_CLASSES,
        "expected.cause_class",
    )
    minimum_confidence_floor = _require_bounds(
        _require_number(payload["minimum_confidence_floor"], "expected.minimum_confidence_floor"),
        LINE_CONFIDENCE_BOUNDS.minimum,
        LINE_CONFIDENCE_BOUNDS.maximum,
        "expected.minimum_confidence_floor",
    )

    allowed_actions_raw = payload["allowed_actions"]
    blocked_actions_raw = payload["blocked_actions"]
    must_emit_events_raw = payload["must_emit_events"]

    if not isinstance(allowed_actions_raw, list):
        raise ScenarioValidationError("expected.allowed_actions must be a list")
    if not isinstance(blocked_actions_raw, list):
        raise ScenarioValidationError("expected.blocked_actions must be a list")
    if not isinstance(must_emit_events_raw, list):
        raise ScenarioValidationError("expected.must_emit_events must be a list")

    allowed_actions = tuple(
        _require_in_set(
            _require_non_empty_string(action, "expected.allowed_actions[]"),
            ALLOWED_ACTIONS,
            "expected.allowed_actions[]",
        )
        for action in allowed_actions_raw
    )
    blocked_actions = tuple(
        _require_in_set(
            _require_non_empty_string(action, "expected.blocked_actions[]"),
            ALLOWED_ACTIONS,
            "expected.blocked_actions[]",
        )
        for action in blocked_actions_raw
    )

    if set(allowed_actions) & set(blocked_actions):
        raise ScenarioValidationError("expected.allowed_actions and blocked_actions must be disjoint")

    must_emit_events = tuple(
        _require_non_empty_string(event_name, "expected.must_emit_events[]")
        for event_name in must_emit_events_raw
    )
    for required in REQUIRED_EVENT_TYPES:
        if required not in must_emit_events:
            raise ScenarioValidationError(
                f"expected.must_emit_events must include required event: {required}"
            )

    return ExpectedBehavior(
        cause_class=cause_class,
        minimum_confidence_floor=minimum_confidence_floor,
        allowed_actions=allowed_actions,
        blocked_actions=blocked_actions,
        must_emit_events=must_emit_events,
    )


def scenario_from_dict(payload: dict[str, Any]) -> Scenario:
    """
    Construct and validate a scenario from a plain dictionary.
    """
    _require_keys(
        payload,
        (
            "schema_version",
            "scenario_id",
            "title",
            "description",
            "metadata",
            "timeline",
            "initial_state",
            "telemetry_channels",
            "faults",
            "expected",
        ),
        "scenario",
    )

    schema_version = _require_non_empty_string(payload["schema_version"], "schema_version")
    if schema_version != "1.0.0":
        raise ScenarioValidationError("schema_version must be exactly '1.0.0' for this repo version")

    metadata = _parse_metadata(payload["metadata"])
    timeline = _parse_timeline(payload["timeline"])
    initial_state = _parse_initial_state(payload["initial_state"])
    telemetry_channels = _parse_telemetry_channels(payload["telemetry_channels"])
    faults = _parse_faults(payload["faults"], scenario_duration_s=timeline.duration_s)
    expected = _parse_expected(payload["expected"])

    return Scenario(
        schema_version=schema_version,
        scenario_id=_require_non_empty_string(payload["scenario_id"], "scenario_id"),
        title=_require_non_empty_string(payload["title"], "title"),
        description=_require_non_empty_string(payload["description"], "description"),
        metadata=metadata,
        timeline=timeline,
        initial_state=initial_state,
        telemetry_channels=telemetry_channels,
        faults=faults,
        expected=expected,
    )


def load_scenario(path: str | Path) -> Scenario:
    """
    Load and validate a scenario from a JSON file.
    """
    scenario_path = Path(path)
    if not scenario_path.exists():
        raise ScenarioValidationError(f"scenario file does not exist: {scenario_path}")

    try:
        payload = json.loads(scenario_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ScenarioValidationError(f"invalid JSON in scenario file: {scenario_path}") from exc

    if not isinstance(payload, dict):
        raise ScenarioValidationError("scenario root must be a JSON object")

    return scenario_from_dict(payload)
