# k8s_sentinel/pack.py

from activegraph.packs import Pack, ObjectType

from .schemas import (
    InvestigationSchema,
    K8sEntitySchema,
    ContextFactSchema,
    AnomalySchema,
    RemediationSchema,
    AlertSchema,
    GoalRequestSchema,
)
from .behaviors.evidence_collector import evidence_collector
from .behaviors.llm_investigator import llm_investigator
from .behaviors.ops_alerter import ops_alerter
from .behaviors.remediation_executor import remediation_executor


OBJECT_TYPES = [
    ObjectType(name="GoalRequest", schema=GoalRequestSchema,
               description="External anomaly trigger."),
    ObjectType(name="Investigation", schema=InvestigationSchema,
               description="A single incident investigation."),
    ObjectType(name="K8sEntity", schema=K8sEntitySchema,
               description="A Kubernetes entity."),
    ObjectType(name="ContextFact", schema=ContextFactSchema,
               description="A piece of collected evidence."),
    ObjectType(name="Anomaly", schema=AnomalySchema,
               description="A diagnosed anomaly."),
    ObjectType(name="Remediation", schema=RemediationSchema,
               description="A proposed or executed remediation."),
    ObjectType(name="Alert", schema=AlertSchema,
               description="A notification sent to the ops team."),
]


k8s_sentinel_pack = Pack(
    name="k8s_sentinel",
    version="0.1.0",
    object_types=OBJECT_TYPES,
    behaviors=[
        evidence_collector,
        llm_investigator,
        ops_alerter,
        remediation_executor,
    ],
    # NOTA: I tool NON sono nel Pack. Vengono passati direttamente
    # agli @llm_behavior che li usano tramite tools=[...]
)
