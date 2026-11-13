"""Tests for the read-only monitoring engine."""
import unittest
from app.operations_monitor import analyze_snapshot


class OperationsMonitorTests(unittest.TestCase):
    def test_alerts_have_evidence_and_human_review(self):
        snapshot = {
            "trucks": [{"id": "T1", "waiting_minutes": 60}],
            "machines": [{"id": "M1", "status": "working", "operator_confirmed": False}],
            "trips": [{"id": "R1", "status": "completed", "delivery_proof": None,
                       "estimated_cost_eur": 100, "actual_cost_eur": 120}],
        }
        before = repr(snapshot)
        alerts = analyze_snapshot(snapshot)
        self.assertEqual(len(alerts), 4)
        self.assertEqual(
            {a["code"] for a in alerts},
            {"TRUCK_LONG_WAIT", "OPERATOR_NOT_CONFIRMED",
             "MISSING_DELIVERY_PROOF", "TRIP_COST_OVERRUN"},
        )
        self.assertTrue(all(a["requires_human_review"] and a["evidence"] for a in alerts))
        self.assertEqual(repr(snapshot), before)

    def test_no_false_positives_for_missing_data(self):
        self.assertEqual(analyze_snapshot({"trucks": [{}], "trips": [{}]}), [])
        self.assertEqual(analyze_snapshot({}), [])


if __name__ == "__main__":
    unittest.main()
