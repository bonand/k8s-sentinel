# k8s_sentinel/pack.py
"""Active Graph pack: ontologia + behaviors."""
from activegraph.packs import Pack, ObjectType

from .schemas import (GoalRequestSchema, InvestigationSchema, K8sEntitySchema,
                      ContextFactSchema, AnomalySchema, RemediationSchema, AlertSchema)
from .behaviors import (evidence_collector, llm_investigator,
                        ops_alerter, remediation_executor)


OBJECT_TYPES = [
    ObjectType(name="GoalRequest", schema=GoalRequestSchema,
               description="External anomaly trigger from ingestion layer."),
    ObjectType(name="Investigation", schema=InvestigationSchema,
               description="A single incident investigation run."),
    ObjectType(name="K8sEntity", schema=K8sEntitySchema,
               description="A Kubernetes entity (Pod, Deployment, Node, Namespace)."),
    ObjectType(name="ContextFact", schema=ContextFactSchema,
               description="A piece of collected evidence (logs, events, history)."),
    ObjectType(name="Anomaly", schema=AnomalySchema,
               description="A diagnosed anomaly with root cause and confidence."),
    ObjectType(name="Remediation", schema=RemediationSchema,
               description="A proposed or executed remediation action."),
    ObjectType(name="Alert", schema=AlertSchema,
               description="A notification sent to the operations team."),
]

# Le relation types sono libere in Active Graph: graph.add_relation accetta
# qualsiasi stringa come type. Le usiamo coerentemente nei behavior:
#   INVESTIGATES, HAS_EVIDENCE, ABOUT, PRODUCED, HAS_REMEDIATION, TRIGGERED_ALERT
# ma non richiedono dichiarazione nel Pack.

k8s_sentinel_pack = Pack(
    name="k8s_sentinel",
    version="0.1.0",
    description="AI Agent for Kubernetes incident response on Active Graph.",
    object_types=OBJECT_TYPES,
    behaviors=[evidence_collector, llm_investigator, ops_alerter, remediation_executor],
)
