"""Deterministic, rule-registered simulation kernel.

This is an auditable classroom engine, not a calibrated model of Starbucks.
Events submit inputs to pre-registered rules; they never author state deltas.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Iterable, Mapping


class EngineError(ValueError):
    """Raised when an event violates the simulation contract."""


@dataclass(frozen=True)
class IndexValue:
    value: float
    base_period: str
    base_value: float = 100.0


@dataclass(frozen=True)
class RuleInvocation:
    rule_id: str
    inputs: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Event:
    event_id: str
    sim_time: str
    event_type: str
    actor: str
    action: str
    sequence: int = 0
    rules: tuple[RuleInvocation, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    player_visible: bool = True
    parallel_group: str | None = None
    depends_on: tuple[str, ...] = ()
    notes: str = ""


RuleFunction = Callable[[dict[str, Any], Mapping[str, Any], Mapping[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class RuleDefinition:
    rule_id: str
    function: RuleFunction
    parameters: Mapping[str, Any]


class RuleRegistry:
    """Registry is frozen by convention after construction; duplicate IDs fail."""

    def __init__(self) -> None:
        self._rules: dict[str, RuleDefinition] = {}

    def register(
        self, rule_id: str, function: RuleFunction,
        parameters: Mapping[str, Any] | None = None,
    ) -> None:
        if not rule_id or rule_id in self._rules:
            raise EngineError(f"Missing or duplicate rule_id: {rule_id!r}")
        self._rules[rule_id] = RuleDefinition(
            rule_id, function, deepcopy(dict(parameters or {}))
        )

    def get(self, rule_id: str) -> RuleDefinition:
        try:
            return self._rules[rule_id]
        except KeyError as exc:
            raise EngineError(f"Unregistered rule_id: {rule_id}") from exc

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._rules))


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


def _rule_charge_energy(state, inputs, params):
    cost = inputs.get("cost")
    if not isinstance(cost, int) or cost < 0:
        raise EngineError("resource.charge cost must be a non-negative integer")
    before = state["decision_energy"]
    if cost > before:
        raise EngineError("Insufficient CEO decision energy")
    return {"decision_energy": before - cost}


def _rule_reconcile_legacy_energy(state, inputs, params):
    before = inputs.get("reported_before")
    displayed_cost = inputs.get("displayed_cost")
    reported_after = inputs.get("reported_after")
    if before != state["decision_energy"]:
        raise EngineError("Legacy balance does not match current engine state")
    if not all(isinstance(x, int) and x >= 0 for x in (displayed_cost, reported_after)):
        raise EngineError("Legacy resource inputs must be non-negative integers")
    derived_delta = before - reported_after
    conflict = {
        "reported_before": before,
        "displayed_cost": displayed_cost,
        "reported_after": reported_after,
        "derived_delta": derived_delta,
        "status": "consistent" if displayed_cost == derived_delta else "conflict",
    }
    audit = list(state.get("legacy_resource_audits", []))
    audit.append(conflict)
    return {"decision_energy": reported_after, "legacy_resource_audits": audit}


def _rule_apply_strategy(state, inputs, params):
    """Transparent illustrative mechanics; parameters are not empirically calibrated."""
    prune = inputs.get("product_prune_units", 0)
    training = inputs.get("training_store_count", 0)
    pilot = inputs.get("pilot_store_count", 0)
    delay = inputs.get("expansion_delay_days", 0)
    for name, value in (("product_prune_units", prune), ("training_store_count", training),
                        ("pilot_store_count", pilot), ("expansion_delay_days", delay)):
        if not isinstance(value, (int, float)) or value < 0:
            raise EngineError(f"{name} must be non-negative")
    if pilot > training:
        raise EngineError("pilot_store_count cannot exceed training_store_count")
    load = training * params["load_per_training_store"] + prune * params["load_per_prune_unit"]
    evidence_gain = pilot * params["evidence_gain_per_pilot_store"]
    return {
        "product_prune_units_cumulative": state["product_prune_units_cumulative"] + prune,
        "training_coverage_stores": state["training_coverage_stores"] + training,
        "organization_load_points": state["organization_load_points"] + load,
        "evidence_quality_points": state["evidence_quality_points"] + evidence_gain,
        "expansion_delay_days": state["expansion_delay_days"] + delay,
    }


def build_default_registry() -> RuleRegistry:
    registry = RuleRegistry()
    registry.register("resource.charge", _rule_charge_energy)
    registry.register("legacy.resource.reconcile", _rule_reconcile_legacy_energy)
    registry.register(
        "strategy.apply_illustrative", _rule_apply_strategy,
        {"load_per_training_store": 0.5, "load_per_prune_unit": 0.2,
         "evidence_gain_per_pilot_store": 0.5},
    )
    return registry


def _apply_rule(state, invocation, registry):
    definition = registry.get(invocation.rule_id)
    outputs = definition.function(
        deepcopy(state), deepcopy(dict(invocation.inputs)), deepcopy(dict(definition.parameters))
    )
    if not isinstance(outputs, dict):
        raise EngineError(f"Rule {invocation.rule_id} must return a dict")
    next_state = deepcopy(state)
    for key, value in outputs.items():
        if key not in state:
            raise EngineError(f"Rule {invocation.rule_id} wrote unknown state key: {key}")
        if key == "decision_energy" and (not isinstance(value, int) or value < 0):
            raise EngineError("decision_energy must remain a non-negative integer")
        if key != "legacy_resource_audits" and type(state[key]) is not type(value):
            raise EngineError(f"Rule {invocation.rule_id} changed type for {key}")
        next_state[key] = value
    return next_state


def apply_event(state, event, seen_ids, registry=None):
    """Apply an event atomically through registered rule functions only."""
    registry = registry or build_default_registry()
    if event.event_id in seen_ids:
        raise EngineError(f"Duplicate event_id: {event.event_id}")
    _parse_time(event.sim_time)
    if not isinstance(event.sequence, int) or event.sequence < 0:
        raise EngineError("sequence must be a non-negative integer")
    next_state = deepcopy(state)
    for invocation in event.rules:
        next_state = _apply_rule(next_state, invocation, registry)
    return next_state


def _event_order(event):
    return (_parse_time(event.sim_time), event.sequence, event.event_id)


def replay_with_trace(initial_state, events, registry=None):
    """Return deterministic snapshots. Parallel work may overlap; state commits serialize."""
    validate_initial_state(initial_state)
    registry = registry or build_default_registry()
    ordered = sorted(list(events), key=_event_order)
    ids = [event.event_id for event in ordered]
    if len(ids) != len(set(ids)):
        raise EngineError("Duplicate event_id in replay")
    known = set()
    state = deepcopy(initial_state)
    trace = [{"event_id": "INITIAL", "state": deepcopy(state)}]
    for event in ordered:
        missing = set(event.depends_on) - known
        if missing:
            raise EngineError(f"Event {event.event_id} has unresolved dependencies: {sorted(missing)}")
        state = apply_event(state, event, known, registry)
        known.add(event.event_id)
        trace.append({"event_id": event.event_id, "state": deepcopy(state)})
    return trace


def replay(initial_state, events, registry=None):
    return replay_with_trace(initial_state, events, registry)[-1]["state"]


def audit_legacy_resource_cost(displayed_cost, balance_before, balance_after):
    derived_delta = balance_before - balance_after
    return {
        "displayed_cost": displayed_cost, "balance_before": balance_before,
        "balance_after": balance_after, "derived_delta": derived_delta,
        "reconciliation_status": "consistent" if displayed_cost == derived_delta else "conflict",
    }


def indexed_product(left: IndexValue, right: IndexValue) -> float:
    """Multiply indices only when both reference the same base period and base value."""
    if left.base_period != right.base_period or left.base_value != right.base_value:
        raise EngineError("Indices do not share the same base period and base value")
    if left.base_value <= 0:
        raise EngineError("Index base must be positive")
    return left.value * right.value / left.base_value


def assess_evidence(evidence):
    """Grade design limitations; never equate a randomized label with proven causality."""
    sampling = evidence.get("sampling_method", "unknown")
    assignment = evidence.get("assignment_method", "unknown")
    confounders = evidence.get("known_confounders", [])
    baseline = evidence.get("baseline_balance")
    if sampling == "unknown" or assignment == "unknown":
        grade = "insufficient_design_information"
    elif assignment == "randomized" and baseline is True and not confounders:
        grade = "randomized_design_candidate"
    elif assignment != "randomized" and baseline is True and evidence.get("controls_documented") is True:
        grade = "quasi_experimental_candidate"
    else:
        grade = "descriptive_only_with_confounders" if confounders else "descriptive_only"
    return {
        "grade": grade, "causal_effect_established": False,
        "known_confounders": list(confounders),
        "reason": "Design classification is a guardrail, not a causal estimate.",
    }


@dataclass(frozen=True)
class Trigger:
    trigger_id: str
    description: str
    predicate: Callable[[Mapping[str, Any]], bool]
    action: str
    no_action_reason: str


def evaluate_triggers(triggers, state, sim_time):
    """Record every evaluated trigger, including those that did not fire."""
    _parse_time(sim_time)
    records = []
    for trigger in sorted(triggers, key=lambda item: item.trigger_id):
        fired = bool(trigger.predicate(state))
        records.append({
            "trigger_id": trigger.trigger_id, "description": trigger.description,
            "checked_at": sim_time, "condition_met": fired,
            "action": trigger.action if fired else None,
            "reason": "trigger_condition_met" if fired else trigger.no_action_reason,
        })
    return records
