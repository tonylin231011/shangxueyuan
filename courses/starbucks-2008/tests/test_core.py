import json
import unittest
from pathlib import Path

from engine.core import (
    EngineError, Event, IndexValue, RuleInvocation, Trigger, assess_evidence,
    audit_legacy_resource_cost, build_default_registry, evaluate_triggers,
    indexed_product, replay, replay_with_trace,
)
from engine.legacy_fixture import build_v1_0_legacy_events


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.registry = build_default_registry()
        self.initial = {
            "decision_energy": 12,
            "legacy_resource_audits": [],
            "board_trust": 7,
            "organization_execution_capacity": 8,
            "brand_trust_index": 100,
            "employee_morale_index": 100,
            "product_prune_units_cumulative": 0,
            "training_coverage_stores": 0,
            "organization_load_points": 0.0,
            "evidence_quality_points": 0.0,
            "expansion_delay_days": 0,
        }

    def event(self, event_id, time, sequence, rule_id, inputs, **kwargs):
        return Event(event_id, time, "execution", "COO", event_id, sequence=sequence,
                     rules=(RuleInvocation(rule_id, inputs),), **kwargs)

    def test_registered_rule_computes_resource_change(self):
        event = self.event("E1", "2008-01-08T09:00:00-08:00", 1,
                           "resource.charge", {"cost": 2})
        self.assertEqual(replay(self.initial, [event], self.registry)["decision_energy"], 10)

    def test_unknown_rule_rejected(self):
        event = self.event("E1", "2008-01-08T09:00:00-08:00", 1,
                           "R-NOT-REGISTERED", {})
        with self.assertRaises(EngineError):
            replay(self.initial, [event], self.registry)

    def test_v1_0_fixture_replays_and_preserves_gaps(self):
        trace = replay_with_trace(self.initial, build_v1_0_legacy_events(), self.registry)
        final = trace[-1]["state"]
        self.assertEqual(final["decision_energy"], 0)
        self.assertEqual(final["legacy_resource_audits"][0]["displayed_cost"], 2)
        self.assertEqual(final["legacy_resource_audits"][0]["derived_delta"], 3)
        self.assertEqual(final["legacy_resource_audits"][0]["status"], "conflict")
        move004 = build_v1_0_legacy_events()[3]
        self.assertIn("No auditable unit pricing", move004.notes)

    def test_same_base_indices_only(self):
        result = indexed_product(IndexValue(100.4, "same-week", 100),
                                 IndexValue(104, "same-week", 100))
        self.assertAlmostEqual(result, 104.416)
        with self.assertRaises(EngineError):
            indexed_product(IndexValue(100.4, "week-a"), IndexValue(104, "week-b"))


    def test_t3_customer_transactions_decomposition(self):
        result = indexed_product(
            IndexValue(96, "FY07-H1", 100),
            IndexValue(95, "FY07-H1", 100),
        )
        self.assertAlmostEqual(result, 91.2)

    def test_evidence_grade_does_not_claim_causality(self):
        result = assess_evidence({
            "sampling_method": "nonrandom", "assignment_method": "manager_selected",
            "baseline_balance": False,
            "known_confounders": ["manager initiative", "schedule changes"],
        })
        self.assertEqual(result["grade"], "descriptive_only_with_confounders")
        self.assertFalse(result["causal_effect_established"])

    def test_parallel_events_have_deterministic_commit_order(self):
        event_b = self.event("B", "2008-01-08T09:00:00-08:00", 1,
                             "resource.charge", {"cost": 2}, parallel_group="batch-1")
        event_a = self.event("A", "2008-01-08T09:00:00-08:00", 1,
                             "resource.charge", {"cost": 1}, parallel_group="batch-1")
        trace = replay_with_trace(self.initial, [event_b, event_a], self.registry)
        self.assertEqual([x["event_id"] for x in trace], ["INITIAL", "A", "B"])
        self.assertEqual(trace[-1]["state"]["decision_energy"], 9)

    def test_unresolved_dependency_rejected(self):
        event = self.event("E2", "2008-01-08T09:00:00-08:00", 2,
                           "resource.charge", {"cost": 1}, depends_on=("MISSING",))
        with self.assertRaises(EngineError):
            replay(self.initial, [event], self.registry)

    def test_t7_two_strategy_paths_from_real_v1_initial_state(self):
        # The five business/governance values are the V1.0 starting snapshot.
        # Additional fields are zeroed engine counters, not empirical business measures.
        aggressive = self.event(
            "A-STRATEGY", "2008-01-12T09:00:00-08:00", 1,
            "strategy.apply_illustrative",
            {"product_prune_units": 3, "training_store_count": 24,
             "pilot_store_count": 0, "expansion_delay_days": 0},
        )
        staged = self.event(
            "B-STRATEGY", "2008-01-12T09:00:00-08:00", 1,
            "strategy.apply_illustrative",
            {"product_prune_units": 0, "training_store_count": 2,
             "pilot_store_count": 2, "expansion_delay_days": 7},
        )
        a = replay(self.initial, [aggressive], self.registry)
        b = replay(self.initial, [staged], self.registry)
        self.assertNotEqual(a, b)
        self.assertGreater(a["organization_load_points"], b["organization_load_points"])
        self.assertGreater(b["evidence_quality_points"], a["evidence_quality_points"])
        self.assertEqual(a["board_trust"], b["board_trust"])
        self.assertEqual(self.registry.get("strategy.apply_illustrative").parameters,
                         {"load_per_training_store": 0.5, "load_per_prune_unit": 0.2,
                          "evidence_gain_per_pilot_store": 0.5})

    def test_trigger_audit_records_fired_and_silent(self):
        triggers = [
            Trigger("T-OPEN", "competitor sees opportunity", lambda s: s["market_opportunity"] > 5,
                    "open_competitor_store", "market opportunity below threshold"),
            Trigger("T-CLOSED", "competitor financing", lambda s: s["financing_available"],
                    "launch_campaign", "financing unavailable"),
        ]
        records = evaluate_triggers(triggers, {"market_opportunity": 2, "financing_available": False},
                                    "2008-01-15T09:00:00-08:00")
        self.assertEqual(len(records), 2)
        by_id = {record["trigger_id"]: record for record in records}
        self.assertFalse(by_id["T-OPEN"]["condition_met"])
        self.assertEqual(by_id["T-OPEN"]["reason"], "market opportunity below threshold")
        self.assertIsNone(by_id["T-CLOSED"]["action"])

    def test_insufficient_energy_rejected(self):
        event = self.event("E1", "2008-01-08T09:00:00-08:00", 1,
                           "resource.charge", {"cost": 13})
        with self.assertRaises(EngineError):
            replay(self.initial, [event], self.registry)

    def test_legacy_cost_helper(self):
        audit = audit_legacy_resource_cost(2, 5, 2)
        self.assertEqual(audit["derived_delta"], 3)
        self.assertEqual(audit["reconciliation_status"], "conflict")


    def test_v1_0_json_fixture_matches_legacy_loader(self):
        fixture_path = Path(__file__).parents[1] / "fixtures" / "v1.0-legacy-moves.json"
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        self.assertEqual([move["move"] for move in fixture["moves"]],
                         ["001", "002", "003", "004", "005"])
        self.assertIn("no auditable unit pricing",
                      fixture["moves"][3]["cost_allocation"].lower())

    def test_execution_queue_can_continue_when_decision_energy_is_zero(self):
        initial = dict(self.initial, decision_energy=0, approved_projects_in_execution=1)
        # An observation event has no new CEO cost and leaves already-authorized work intact.
        event = Event("OBS", "2008-01-20T09:00:00-08:00", "observation", "CEO",
                      "observe approved work", sequence=1)
        result = replay(initial, [event], self.registry)
        self.assertEqual(result["decision_energy"], 0)
        self.assertEqual(result["approved_projects_in_execution"], 1)

    def test_rule_parameters_are_immutable_after_registration(self):
        parameters = self.registry.get("strategy.apply_illustrative").parameters
        with self.assertRaises(TypeError):
            parameters["load_per_training_store"] = 99

    def test_duplicate_event_id_rejected(self):
        event = self.event("DUP", "2008-01-08T09:00:00-08:00", 1,
                           "resource.charge", {"cost": 1})
        with self.assertRaises(EngineError):
            replay(self.initial, [event, event], self.registry)


if __name__ == "__main__":
    unittest.main()
