# path: k8s_sentinel/behaviors/ops_alerter.py
"""Dispatcher di notifica deterministico: Alert -> Slack/PagerDuty."""
import datetime as dt
import os

from activegraph import behavior


def _now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


@behavior(name="sentinel.ops_alerter", on=["alert.created"])
def ops_alerter(event, graph, ctx):
    alert = graph.get_object(event.payload["alert_id"])
    if alert is None:
        return

    anomaly = None
    if event.payload.get("anomaly_id"):
        anomaly = graph.get_object(event.payload["anomaly_id"])

    # Remediation collegata (se gia' esistente, es. ramo auto-approved)
    rem = None
    if anomaly:
        for rel in graph.relations(source=anomaly.id, type="HAS_REMEDIATION"):
            rem = graph.get_object(rel.target)
            break

    # Investigation per recuperare anomaly_type e il deep-link
    inv = None
    if anomaly and anomaly.data.get("investigation_id"):
        inv = graph.get_object(anomaly.data["investigation_id"])

    severity = event.payload.get("severity", "P3")
    channels = ["slack"] + (["pagerduty"] if severity == "P1" else [])

    # Link "inspect trace" verso la dashboard (deep-link ?investigation=)
    inspect_url = None
    inspect_base = os.getenv("ACTIVEGRAPH_INSPECT_URL", "")
    if inspect_base and inv:
        inspect_url = f"{inspect_base}/?investigation={inv.id}"

    params = {
        "anomaly_id": anomaly.data.get("anomaly_id") if anomaly else "unknown",
        "severity": severity,
        "entity_type": anomaly.data.get("affected_entity_type") if anomaly else "unknown",
        "entity_name": anomaly.data.get("affected_entity_name") if anomaly else "unknown",
        "namespace": anomaly.data.get("affected_entity_namespace") if anomaly else "unknown",
        "anomaly_type": inv.data.get("anomaly_type") if inv else "unknown",
        "root_cause_summary": anomaly.data.get("root_cause_summary") if anomaly else "n/a",
        "evidence": anomaly.data.get("root_cause_evidence", []) if anomaly else [],
        "remediation_action": rem.data.get("action") if rem else "pending approval",
        "remediation_reasoning": rem.data.get("reasoning") if rem else "n/a",
        "approval_status": rem.data.get("status") if rem else "pending",
        "channels": channels,
        "inspect_url": inspect_url,
    }

    try:
        result, status = ctx.call("send_ops_alert", **params), "delivered"
    except Exception as e:
        result, status = {"error": str(e)}, "failed"

    graph.patch_object(alert.id, {
        "status": status,
        "delivered_at": _now(),
        "delivery_result": result,
        "channels": channels,
    })

    graph.emit(f"alert.{status}", {
        "alert_id": alert.id,
        "anomaly_id": event.payload.get("anomaly_id"),
        "channels": channels,
    })
