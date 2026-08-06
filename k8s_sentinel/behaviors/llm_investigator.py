# path: k8s_sentinel/behaviors/llm_investigator.py
"""Agentic investigation via @llm_behavior with tool loop."""
import datetime as dt
import os
from activegraph import llm_behavior
from ..prompts import SENTINEL_SYSTEM_PROMPT
from ..schemas import InvestigationResult
from ..tools import (query_cluster_events, query_service_logs,
                     get_deployment_history, get_node_resource_status)

def _now(): return dt.datetime.now(dt.timezone.utc).isoformat()

@llm_behavior(name="sentinel.llm_investigator",
              on=["evidence.collected"],
              description=SENTINEL_SYSTEM_PROMPT,
              output_schema=InvestigationResult,
              tools=[query_cluster_events, query_service_logs,
                     get_deployment_history, get_node_resource_status],
              model=os.getenv("SENTINEL_LLM_MODEL", "claude-sonnet-4-5"),
             )
def llm_investigator(event, graph, ctx, llm_output: InvestigationResult):
    inv = graph.get_object(event.payload["investigation_id"])
    if inv is None: return

    anomaly = graph.add_object("Anomaly", {
        "anomaly_id": llm_output.anomaly_id, "severity": llm_output.severity,
        "affected_entity_type": llm_output.affected_entity.type,
        "affected_entity_name": llm_output.affected_entity.name,
        "affected_entity_namespace": llm_output.affected_entity.namespace,
        "root_cause_summary": llm_output.root_cause.summary,
        "root_cause_evidence": llm_output.root_cause.evidence,
        "confidence": llm_output.root_cause.confidence,
        "detected_at": _now(), "investigation_id": inv.id},
        actor="sentinel.llm_investigator", caused_by=event.id)
    graph.add_relation(inv.id, anomaly.id, "PRODUCED", {"created_at": _now()},
                       actor="sentinel.llm_investigator", caused_by=event.id)

    rem = llm_output.remediation
    if rem.requires_approval:
        # Propone: l'oggetto Remediation esiste solo dopo approval.granted
        ctx.propose_object("Remediation", data={
            "action": rem.action, "target": rem.target, "reasoning": rem.reasoning,
            "expected_outcome": rem.expected_outcome, "risks": rem.risks,
            "requires_approval": True, "status": "proposed",
            "anomaly_id": anomaly.id, "proposed_at": _now()},
            reason=f"Remediation for {llm_output.anomaly_id}")
    else:
        robj = graph.add_object("Remediation", {
            "action": rem.action, "target": rem.target, "reasoning": rem.reasoning,
            "expected_outcome": rem.expected_outcome, "risks": rem.risks,
            "requires_approval": False, "status": "auto_approved",
            "anomaly_id": anomaly.id, "proposed_at": _now()},
            actor="sentinel.llm_investigator", caused_by=event.id)
        graph.add_relation(anomaly.id, robj.id, "HAS_REMEDIATION", {"created_at": _now()},
                           actor="sentinel.llm_investigator", caused_by=event.id)

    if llm_output.alert_team and llm_output.alert_message:
        alert = graph.add_object("Alert", {"severity": llm_output.severity,
                 "message": llm_output.alert_message, "anomaly_id": anomaly.id,
                 "status": "pending", "created_at": _now()},
                 actor="sentinel.llm_investigator", caused_by=event.id)
        graph.add_relation(anomaly.id, alert.id, "TRIGGERED_ALERT", {"created_at": _now()},
                           actor="sentinel.llm_investigator", caused_by=event.id)
        graph.emit("alert.created", {"alert_id": alert.id, "anomaly_id": anomaly.id,
                   "severity": llm_output.severity})

    graph.patch_object(inv.id, {"status": "completed", "completed_at": _now(),
                                "anomaly_id": anomaly.id})
    graph.emit("investigation.completed", {"investigation_id": inv.id,
               "anomaly_id": anomaly.id})
