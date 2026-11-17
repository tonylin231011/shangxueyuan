import unittest
from engine.core import EngineError, Event, StateChange, audit_legacy_resource_cost, indexed_product, replay


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.initial = {"decision_energy": 12, "board_trust": 7, "employee_morale_index": 100, "approved_projects": 9}

    def test_event_cost_and_state_change(self):
        event = Event("EVT-001", "2008-01-08T09:00:00-08:00", "player_action", "CEO",
                      "authorize_store_research", 2,
                      changes=(StateChange("approved_projects", 9, 7, "RULE-APPROVAL-01", "projects"),))
        result = replay(self.initial, [event])
        self.assertEqual(result["decision_energy"], 10)
        self.assertEqual(result["approved_projects"], 7)

    def test_replay_is_deterministic(self):
        events = [
            Event("E1", "2008-01-08T09:00:00-08:00", "player_action", "CEO", "act", 1,
                  changes=(StateChange("board_trust", 7, 6, "R1", "score"),)),
            Event("E2", "2008-01-09T09:00:00-08:00", "npc_action", "CFO", "report",
                  changes=(StateChange("employee_morale_index", 100, 101, "R2", "index"),)),
        ]
        self.assertEqual(replay(self.initial, events), replay(self.initial, events))

    def test_legacy_cost_conflict_is_preserved(self):
        audit = audit_legacy_resource_cost(2, 5, 2)
        self.assertEqual(audit["derived_delta"], 3)
        self.assertEqual(audit["reconciliation_status"], "conflict")
        self.assertEqual(audit["displayed_cost"], 2)

    def test_index_identity(self):
        self.assertAlmostEqual(indexed_product(100.4, 104, 100), 104.416)
        self.assertAlmostEqual(indexed_product(96, 95, 100), 91.2)

    def test_precondition_mismatch_rejected(self):
        event = Event("E1", "2008-01-08T09:00:00-08:00", "execution", "COO", "bad update",
                      changes=(StateChange("board_trust", 6, 5, "R1", "score"),))
        with self.assertRaises(EngineError):
            replay(self.initial, [event])

    def test_negative_resources_rejected(self):
        event = Event("E1", "2008-01-08T09:00:00-08:00", "player_action", "CEO", "too costly", 13)
        with self.assertRaises(EngineError):
            replay(self.initial, [event])

    def test_duplicate_event_rejected(self):
        event = Event("E1", "2008-01-08T09:00:00-08:00", "observation", "COO", "note")
        with self.assertRaises(EngineError):
            replay(self.initial, [event, event])

    def test_events_must_be_time_ordered(self):
        later = Event("E2", "2008-01-09T09:00:00-08:00", "observation", "COO", "later")
        earlier = Event("E1", "2008-01-08T09:00:00-08:00", "observation", "COO", "earlier")
        with self.assertRaises(EngineError):
            replay(self.initial, [later, earlier])


if __name__ == "__main__":
    unittest.main()
