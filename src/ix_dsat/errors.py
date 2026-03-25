class DSATError(Exception):
    """Base exception for IX-Deep-Space-Anomaly-Triage."""


class ScenarioValidationError(DSATError):
    """Raised when a scenario contract is invalid."""
