# path: k8s_sentinel/behaviors/evidence_collector.py
"""Deterministic evidence collection on GoalRequest."""
import datetime as dt
from activegraph import behavior

def _now(): return dt.datetime.now(dt.timezone.utc).isoformat()

def _ext_id(p):
    ts = str(p.get("timestamp") or _now())[:16]
    return f"{p.get('namespace','?')}:{p.get('pod_name','ns')}:{p.get('anomaly_type','?')}:{ts}"

@behavior(name="sentinel.evidence_collector",
          on=["object.created"], where={"object.type": "GoalRequest"})
def evidence_collector(event, graph, ctx):
    req = graph.get_object(event.payload["object"]["id"])
    if req is None: return
    p = req.data or {}
    if p.get("kind") != "anomaly": return
    ns, pod = p.get("namespace"), p.get("pod_name")
    if not ns:
        graph.emit("goal.rejected", {"reason": "missing_namespace"}); return
    ext = p.get("incident_id") or _ext_id(p)
    if any(o.data.get("external_id") == ext for o in graph.objects(type="Investigation")):
        graph.emit("investigation.deduplicated", {"external_id": ext}); return

    inv = graph.add_object("Investigation", {
        "external_id": ext, "status": "collecting_evidence",
        "anomaly_type": p.get("anomaly_type", "Unknown"), "severity": p.get("severity", "P3"),
        "namespace": ns, "pod_name": pod, "source": p.get("source"),
        "goal_request_id": req.id, "opened_at": _now()},
        actor="sentinel.evidence_collector", caused_by=event.id)

    kind, name = ("Pod", pod) if pod else ("Namespace", ns)
    entity = graph.add_object("K8sEntity", {"kind": kind, "name": name,
                              "namespace": ns, "created_at": _now()},
                              actor="sentinel.evidence_collector", caused_by=event.id)
    graph.add_relation(inv.id, entity.id, "INVESTIGATES", {"created_at": _now()},
                       actor="sentinel.evidence_collector", caused_by=event.id)

    q = {"namespace": ns, "pod_name": pod, "include_normal": False,
         "since_minutes": 15, "limit": 50}
    try:
        content, status = ctx.call("query_cluster_events", **q), "ok"
    except Exception as e:
        content, status = {"error": str(e), "query": q}, "error"

    fact = graph.add_object("ContextFact", {"kind": "cluster_events", "status": status,
             "query": q, "content": content, "collected_at": _now(),
             "collector": "sentinel.evidence_collector"},
             actor="sentinel.evidence_collector", caused_by=event.id)
    graph.add_relation(inv.id, fact.id, "HAS_EVIDENCE", {"evidence_type": "cluster_events"},
                       actor="sentinel.evidence_collector", caused_by=event.id)
    graph.add_relation(fact.id, entity.id, "ABOUT", {},
                       actor="sentinel.evidence_collector", caused_by=event.id)
    graph.emit("evidence.collected", {"investigation_id": inv.id, "entity_id": entity.id,
               "evidence_fact_id": fact.id, "anomaly_type": p.get("anomaly_type"),
               "severity": p.get("severity"), "namespace": ns, "pod_name": pod,
               "evidence_status": status})
