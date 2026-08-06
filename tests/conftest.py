"""Fixtures condivisi: runtime, goal, stub LLM e mock al confine client."""
import json
import datetime as dt
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch

import pytest
from activegraph import Runtime, Graph

from k8s_sentinel.pack import k8s_sentinel_pack

FIX = Path(__file__).parent / "fixtures"


class StubProvider:
    """Provider LLM deterministico per i test."""
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
        "remediation": {"action": "Restart deployment payments-api",
                        "target": "payments-api", "reasoning": "apply new limits",
                        "expected_outcome": "no OOM", "risks": "brief disruption",
                        "requires_approval": True},
        "alert_team": True, "alert_message": "OOM detected"}
    return runtime


def _k8s_event(e):
    ts = dt.datetime.fromisoformat(e["last_timestamp"])
    return NS(type=e["type"], reason=e["reason"], message=e["message"],
              count=e["count"], last_timestamp=ts, first_timestamp=ts, event_time=None,
              involved_object=NS(kind=e["object_kind"], name=e["object_name"],
                                 namespace=e["object_namespace"]),
              source=NS(component=e.get("source_component")),
              metadata=NS(creation_timestamp=ts))


class _Resp:
    def __init__(self, payload): self._p = payload
    def raise_for_status(self): pass
    def json(self): return self._p


@pytest.fixture
def patch_read_only_tools(oom_events):
    """Mock al confine client (K8s/HTTP), NON sui tool: ctx.call dispatcha
    tramite il registry popolato al decorator, quindi i tool reali restano
    invariati e vengono mockati i loro client sottostanti."""
    items = [_k8s_event(e) for e in oom_events["events"]]
    core = NS(list_namespaced_event=lambda **kw: NS(items=items),
              list_event_for_all_namespaces=lambda **kw: NS(items=items),
              delete_namespaced_pod=lambda **kw: None,
              list_node=lambda **kw: NS(items=[]))
    apps = NS(patch_namespaced_deployment=lambda **kw: None,
              patch_namespaced_deployment_scale=lambda **kw: None,
              list_namespaced_deployment=lambda **kw: NS(items=[]),
              list_namespaced_replica_set=lambda **kw: NS(items=[]))
    with patch("k8s_sentinel.tools.query_cluster_events.get_core_v1_api", return_value=core), \
         patch("k8s_sentinel.tools.execute_remediation.get_core_v1_api", return_value=core), \
         patch("k8s_sentinel.tools.execute_remediation.get_apps_v1_api", return_value=apps), \
         patch("k8s_sentinel.tools.execute_remediation.EXECUTION_ENABLED", True), \
         patch("k8s_sentinel.tools.execute_remediation.ALLOWED_NS", []), \
         patch("k8s_sentinel.tools.get_deployment_history.get_apps_v1_api", return_value=apps), \
         patch("k8s_sentinel.tools.get_node_resource_status.get_core_v1_api", return_value=core), \
         patch("k8s_sentinel.tools.query_service_logs.LOKI_URL", "http://loki:3100"), \
         patch("k8s_sentinel.tools.query_service_logs.requests.get",
               return_value=_Resp({"data": {"result": []}})), \
         patch("k8s_sentinel.tools.send_ops_alert.SLACK_WEBHOOK_URL", "http://hooks.slack/x"), \
         patch("k8s_sentinel.tools.send_ops_alert.requests.post", return_value=_Resp({})):
        yield
