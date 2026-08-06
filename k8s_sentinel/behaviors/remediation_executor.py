# path: k8s_sentinel/behaviors/remediation_executor.py
"""Executes approved remediations (dry-run then real)."""
import datetime as dt, re
from activegraph import behavior

def _now(): return dt.datetime.now(dt.timezone.utc).isoformat()

def _parse(data):
    text = (data.get("action") or "").lower(); target = data.get("target", "")
    name = target.split("/")[-1]
    if "restart" in text and "deployment" in target.lower():
        return {"action": "restart_deployment", "target_name": name}
    if "delete pod" in text or "restart pod" in text:
        return {"action": "delete_pod", "target_name": name}
    if "scale" in text:
        m = re.search(r"(\d+)\s*replicas?", text)
        return {"action": "scale_deployment", "target_name": name,
                "replicas": int(m.group(1)) if m else 1}
    return None

@behavior(name="sentinel.remediation_executor", on=["approval.granted"])
def remediation_executor(event, graph, ctx):
    obj_id = event.payload.get("object_id"); appr_id = event.payload.get("id")
    if not obj_id: return
    rem = graph.get_object(obj_id)
    if rem is None or rem.type != "Remediation": return
    data = rem.data or {}
    anomaly = graph.get_object(data.get("anomaly_id")) if data.get("anomaly_id") else None
    ns = anomaly.data.get("affected_entity_namespace") if anomaly else None
    if not ns:
        graph.emit("remediation.execution_failed",
                   {"reason": "missing_namespace", "remediation_id": obj_id}); return
    if anomaly:
        graph.add_relation(anomaly.id, obj_id, "HAS_REMEDIATION",
                           {"approved_via": appr_id, "created_at": _now()},
                           actor="sentinel.remediation_executor", caused_by=event.id)
    spec = _parse(data)
    if spec is None:
        graph.patch_object(obj_id, {"status": "approved_but_unexecutable",
                                    "approval_id": appr_id}); return
    # Fase 1: dry-run
    try:
        dry = ctx.call("execute_remediation", action=spec["action"], namespace=ns,
                       target_name=spec["target_name"],
                       replicas=spec.get("replicas", 1), dry_run=True)
    except Exception as e:
        graph.patch_object(obj_id, {"status": "dry_run_failed", "approval_id": appr_id,
                                    "dry_run_result": {"error": str(e)}}); return
    # Fase 2: esecuzione reale
    try:
        res = ctx.call("execute_remediation", action=spec["action"], namespace=ns,
                       target_name=spec["target_name"],
                       replicas=spec.get("replicas", 1), dry_run=False)
        status = "executed"
    except Exception as e:
        res, status = {"error": str(e)}, "failed"
    graph.patch_object(obj_id, {"status": status, "approval_id": appr_id,
                                "executed_at": _now(), "execution_result": res})
    graph.emit(f"remediation.{status}", {"remediation_id": obj_id,
               "action": spec["action"], "target": f"{ns}/{spec['target_name']}"})
