# path: tests/conftest.py
import json
from pathlib import Path
import pytest
from activegraph import Runtime, Graph
from k8s_sentinel.pack import k8s_sentinel_pack

FIX = Path(__file__).parent / "fixtures"

class StubProvider:
    """Deterministic LLM stub; patched per-test via mock_llm_response."""
    def __init__(self): self.response = {}
    def generate(self, *a, **k): return self.response

@pytest.fixture
def runtime():
    rt = Runtime(Graph(), llm_provider=StubProvider())
    rt.load_pack(k8s_sentinel_pack)
    return rt

@pytest.fixture
def oom_goal():
    return {"kind": "anomaly", "incident_id": "test-oom-001", "namespace": "production",
            "pod_name": "payments-api-7f9d8c-x9z2", "anomaly_type": "OOMKilled",
            "severity": "P2", "source": "test"}

@pytest.fixture
def oom_events():
    return json.load(open(FIX / "oom_incident.json"))

@pytest.fixture
def mock_llm(runtime):
    runtime.llm_provider.response = {
        "anomaly_id": "test-oom-001", "severity": "P2",
        "affected_entity": {"type": "Pod", "name": "payments-api-7f9d8c-x9z2",
                            "namespace": "production"},
        "root_cause": {"summary": "OOMKilled: memory limit insufficient",
                       "evidence": ["event OOMKilling"], "confidence": 0.95},
        "remediation": {"action": "Restart deployment payments-api", "target": "payments-api",
                        "reasoning": "apply new limits", "expected_outcome": "no OOM",
                        "risks": "brief disruption", "requires_approval": True},
        "alert_team": True, "alert_message": "OOM detected"}
    return runtime
