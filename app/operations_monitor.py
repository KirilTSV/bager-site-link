"""Deterministic, explainable monitoring rules for BAGER SITE LINK.

No network access, no automatic mutations, no AI model claims.
Caller supplies validated operational snapshots; alerts are recommendations only.
"""
from datetime import datetime, timezone
from typing import Any, Mapping


def analyze_snapshot(snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return traceable alerts from a snapshot without modifying its records.

    Expected optional arrays: trucks, machines, trips.
    All durations are minutes; costs are EUR.
    """
    alerts: list[dict[str, Any]] = []
    observed_at = datetime.now(timezone.utc).isoformat()

    def add(code: str, severity: str, entity_type: str, entity_id: str,
            evidence: dict[str, Any], recommendation: str) -> None:
        alerts.append({
            "code": code, "severity": severity,
            "entity_type": entity_type, "entity_id": entity_id,
            "evidence": evidence, "recommendation": recommendation,
            "observed_at": observed_at, "source": "rule_engine_v1",
            "requires_human_review": True,
        })

    for truck in snapshot.get("trucks", []):
        truck_id = str(truck.get("id", "unknown"))
        wait = truck.get("waiting_minutes")
        if isinstance(wait, (int, float)) and not isinstance(wait, bool) and wait > 45:
            add("TRUCK_LONG_WAIT", "warning", "truck", truck_id,
                {"waiting_minutes": wait, "threshold_minutes": 45},
                "Провери причината за престоя и синхронизацията с багера.")

    for machine in snapshot.get("machines", []):
        machine_id = str(machine.get("id", "unknown"))
        status = machine.get("status")
        if status == "working" and machine.get("operator_confirmed") is False:
            add("OPERATOR_NOT_CONFIRMED", "critical", "machine", machine_id,
                {"status": status, "operator_confirmed": False},
                "Потвърди оператора преди да приемеш отчета за работа.")

    for trip in snapshot.get("trips", []):
        trip_id = str(trip.get("id", "unknown"))
        if trip.get("status") == "completed" and not trip.get("delivery_proof"):
            add("MISSING_DELIVERY_PROOF", "warning", "trip", trip_id,
                {"status": "completed", "delivery_proof_present": False},
                "Изискай доказателство за завършен курс.")
        estimated = trip.get("estimated_cost_eur")
        actual = trip.get("actual_cost_eur")
        if (all(isinstance(x, (int, float)) and not isinstance(x, bool)
                for x in (estimated, actual)) and estimated > 0
                and actual > estimated * 1.15):
            add("TRIP_COST_OVERRUN", "warning", "trip", trip_id,
                {"estimated_cost_eur": estimated, "actual_cost_eur": actual,
                 "threshold_ratio": 1.15},
                "Провери разхода и причината за превишението.")

    return alerts
