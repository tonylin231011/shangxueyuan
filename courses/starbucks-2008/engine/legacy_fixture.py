"""V1.0 original moves loaded as the first auditable engine fixture."""
from .core import Event, RuleInvocation


def build_v1_0_legacy_events() -> list[Event]:
    """Preserve package costs and the MOVE 003 conflict; do not invent task prices."""
    return [
        Event(
            "V1-MOVE-001", "2008-01-07T07:30:00-08:00", "player_action", "CEO",
            "Original MOVE 001: request regional report and COO response", sequence=1,
            rules=(RuleInvocation("resource.charge", {"cost": 2}),),
            notes="Package cost recorded as 2; sub-action allocation was not itemized.",
        ),
        Event(
            "V1-MOVE-002", "2008-01-08T09:00:00-08:00", "player_action", "CEO",
            "Original MOVE 002: three parallel investigations", sequence=2,
            rules=(RuleInvocation("resource.charge", {"cost": 5}),),
            parallel_group="MOVE-002-investigations",
            notes="Three investigations ran in parallel; package cost 5; task-level cost/timestamps unavailable.",
        ),
        Event(
            "V1-MOVE-003", "2008-01-11T12:00:00-08:00", "player_approval", "CEO",
            "Original MOVE 003: approve three management requests", sequence=3,
            rules=(RuleInvocation("legacy.resource.reconcile", {
                "reported_before": 5, "displayed_cost": 2, "reported_after": 2,
            }),),
            notes="Preserves displayed cost 2 and balance-derived delta 3 as a conflict.",
        ),
        Event(
            "V1-MOVE-004", "2008-01-12T09:00:00-08:00", "player_action", "CEO",
            "Original MOVE 004: expansion pause, product review, staff training", sequence=4,
            rules=(RuleInvocation("resource.charge", {"cost": 2}),),
            notes="Package cost 2 is recorded. No auditable unit pricing exists for each sub-action.",
        ),
        Event(
            "V1-MOVE-005", "2008-01-14T09:00:00-08:00", "observation", "CEO",
            "Original MOVE 005: inspect execution and validation", sequence=5,
            notes="Six-day observation of previously authorized work; no new decision-energy cost.",
        ),
    ]
