# path: k8s_sentinel/schemas.py
"""Pydantic schemas for LLM output and graph object types."""
from typing import Optional, List, Any
from pydantic import BaseModel, Field


# --- LLM output ---
class AffectedEntity(BaseModel):
    type: str
    name: str
    namespace: Optional[str] = None

class RootCause(BaseModel):
    summary: str
    evidence: List[str] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)

class RemediationSpec(BaseModel):
    action: str
    target: str
    reasoning: str
    expected_outcome: str
    risks: str
    requires_approval: bool = True

class InvestigationResult(BaseModel):
    anomaly_id: str
    severity: str = Field(pattern="^(P1|P2|P3)$")
    affected_entity: AffectedEntity
    root_cause: RootCause
    remediation: RemediationSpec
    alert_team: bool
    alert_message: Optional[str] = None


# --- Graph object types ---
class GoalRequestSchema(BaseModel):
    kind: str = "anomaly"
    incident_id: Optional[str] = None
    namespace: Optional[str] = None
    pod_name: Optional[str] = None
    deployment: Optional[str] = None
    anomaly_type: Optional[str] = None
    severity: Optional[str] = "P3"
    source: Optional[str] = None
    timestamp: Optional[str] = None
    log_hint: Optional[str] = None

class InvestigationSchema(BaseModel):
    external_id: str
    status: str = "collecting_evidence"
    anomaly_type: Optional[str] = None
    severity: Optional[str] = None
    namespace: Optional[str] = None
    pod_name: Optional[str] = None
    source: Optional[str] = None
    goal_request_id: Optional[str] = None
    opened_at: Optional[str] = None
    completed_at: Optional[str] = None
    anomaly_id: Optional[str] = None

class K8sEntitySchema(BaseModel):
    kind: str
    name: str
    namespace: Optional[str] = None
    created_at: Optional[str] = None

class ContextFactSchema(BaseModel):
    kind: str
    status: str = "ok"
    query: Optional[dict] = None
    content: Optional[dict] = None
    collected_at: Optional[str] = None
    collector: Optional[str] = None

class AnomalySchema(BaseModel):
    anomaly_id: str
    severity: str
    affected_entity_type: Optional[str] = None
    affected_entity_name: Optional[str] = None
    affected_entity_namespace: Optional[str] = None
    root_cause_summary: Optional[str] = None
    root_cause_evidence: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    detected_at: Optional[str] = None
    investigation_id: Optional[str] = None

class RemediationSchema(BaseModel):
    action: str
    target: str
    reasoning: Optional[str] = None
    expected_outcome: Optional[str] = None
    risks: Optional[str] = None
    requires_approval: bool = True
    status: str = "proposed"
    anomaly_id: Optional[str] = None
    proposed_at: Optional[str] = None
    approval_id: Optional[str] = None
    executed_at: Optional[str] = None
    execution_result: Optional[Any] = None

class AlertSchema(BaseModel):
    severity: str
    message: Optional[str] = None
    anomaly_id: Optional[str] = None
    status: str = "pending"
    created_at: Optional[str] = None
    delivered_at: Optional[str] = None
    delivery_result: Optional[Any] = None
    channels: List[str] = Field(default_factory=list)
