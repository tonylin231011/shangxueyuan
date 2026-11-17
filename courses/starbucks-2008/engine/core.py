"""Deterministic event-ledger prototype for the Starbucks 2008 simulation.

This is a small rules kernel, not a calibrated model of Starbucks' business.
It only applies explicit, auditable state changes supplied by a simulation author.
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable


class EngineError(ValueError):
    """Raised when an event violates the simulation contract."""


@dataclass(frozen=True)
class StateChange:
    key: str
    before: Any
    after: Any
    rule_id: str
    unit: str | None = None


@dataclass(frozen=True)
class Event:
    event_id: str
    sim_time: str
    event_type: str
    actor: str
    action: str
    decision_energy_cost: int = 0
    calendar_hours: float = 0
    changes: tuple[StateChange, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    player_visible: bool = True
    notes: str = ""


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise EngineError(f"Invalid ISO-8601 simulation time: {value}") from exc
    if parsed.tzinfo is None:
        raise EngineError("sim_time must include an explicit UTC offset")
    return parsed


def validate_initial_state(state: dict[str, Any]) -> None:
    if not isinstance(state, dict):
        raise EngineError("Initial state must be a JSON-like object")
    if "decision_energy" not in state:
        raise EngineError("Initial state must define decision_energy")
    if not isinstance(state["decision_energy"], int) or state["decision_energy"] < 0:
        raise EngineError("decision_energy must be a non-negative integer")


def apply_event(state: dict[str, Any], event: Event, seen_ids: set[str]) -> dict[str, Any]:
    """Apply one event atomically; never mutates the input state."""
    if event.event_id in seen_ids:
        raise EngineError(f"Duplicate event_id: {event.event_id}")
    _parse_time(event.sim_time)
    if event.decision_energy_cost < 0 or event.calendar_hours < 0:
        raise EngineError("Event costs cannot be negative")
    if event.decision_energy_cost > state.get("decision_energy", 0):
        raise EngineError("Insufficient CEO decision energy")

    next_state = deepcopy(state)
    next_state["decision_energy"] -= event.decision_energy_cost
    changed_keys: set[str] = set()
    for change in event.changes:
        if change.key == "decision_energy":
            raise EngineError("decision_energy is changed only through event cost")
        if change.key in changed_keys:
            raise EngineError(f"Duplicate state change for key: {change.key}")
        changed_keys.add(change.key)
        if change.key not in next_state:
            raise EngineError(f"Unknown state key: {change.key}")
        if next_state[change.key] != change.before:
            raise EngineError(
                f"Precondition mismatch for {change.key}: "
                f"expected {change.before!r}, found {next_state[change.key]!r}"
            )
        if not change.rule_id.strip():
            raise EngineError(f"Missing rule_id for state change: {change.key}")
        if type(change.before) is not type(change.after):
            raise EngineError(f"Type change is not allowed for state key: {change.key}")
        next_state[change.key] = change.after
    return next_state


def replay(initial_state: dict[str, Any], events: Iterable[Event]) -> dict[str, Any]:
    """Replay an ordered event sequence deterministically."""
    validate_initial_state(initial_state)
    state = deepcopy(initial_state)
    seen: set[str] = set()
    previous_time: datetime | None = None
    for event in events:
        current_time = _parse_time(event.sim_time)
        if previous_time is not None and current_time < previous_time:
            raise EngineError("Events must be ordered by non-decreasing sim_time")
        state = apply_event(state, event, seen)
        seen.add(event.event_id)
        previous_time = current_time
    return state


def audit_legacy_resource_cost(displayed_cost: int, balance_before: int, balance_after: int) -> dict[str, Any]:
    """Report legacy ledger mismatch without rewriting the source record."""
    derived_delta = balance_before - balance_after
    return {
        "displayed_cost": displayed_cost,
        "balance_before": balance_before,
        "balance_after": balance_after,
        "derived_delta": derived_delta,
        "reconciliation_status": "consistent" if displayed_cost == derived_delta else "conflict",
    }


def indexed_product(left_index: float, right_index: float, base: float = 100.0) -> float:
    """Combine two indices only when they share the same declared base."""
    if base <= 0:
        raise EngineError("Index base must be positive")
    return left_index * right_index / base


def descriptive_only(evidence: dict[str, Any]) -> bool:
    """Conservative guard: non-random/unknown sampling is not causal evidence."""
    return evidence.get("sampling_method") != "randomized"
