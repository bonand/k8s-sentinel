# path: k8s_sentinel/behaviors/ops_alerter.py
"""Deterministic notification dispatcher."""
import datetime as dt, os
from activegraph import behavior

def _now(): return dt.datetime.now(dt.timezone.utc).isoformat()

@behavior(name="sentinel.ops_alerter", on=["alert.created"])
def ops_alerter(event, graph, ctx):
    alert = graph.get_object(event.payload["alert_id"])
    if alert is None: return
    anomaly = graph.get_object(event.payload.get("anomaly_id")) if event.payload.get("anomaly_id") else None
    rem = None
    if anomaly:
        for rel in graph.relations(source=anomaly.id, type="HAS_REMEDIATION"):
            rem = graph.get_object(rel.target); break
    channels = ["slack"] + (["pagerduty"] if event.payload.get("severity") == "P1" else [])
    params = {
        "anomaly_id": anomaly.data.get("anomaly_id") if anomaly else "unknown",
        "severity": event.payload.get("severity", "P3"),
        "entity_type": anomaly.data.get("affected_entity_type") if anomaly else "unknown",
        "entity_name": anomaly.data.get("affected_entity_name") if anomaly else "unknown",
        "namespace": anomaly.data.get("affected_entity_namespace") if anomaly else "unknown",
        "anomaly_type": "unknown",
        "root_cause_summary": anomaly.data.get("root_cause_summary") if anomaly else "n/a",
        "evidence": anomaly.data.get("root_cause_evidence", []) if anomaly else [],
        "remediation_action": rem.data.get("action") if rem else "none",
        "remediation_reasoning": rem.data.get("reasoning") if rem else "n/a",
        "channels": channels,
    }
    try:
        result, status = ctx.call("send_ops_alert", **params), "delivered"
    except Exception as e:
        result, status = {"error": str(e)}, "failed"
    graph.patch_object(alert.id, {"status": status, "delivered_at": _now(),
                                  "delivery_result": result, "channels": channels})
    graph.emit(f"alert.{status}", {"alert_id": alert.id, "channels": channels})
