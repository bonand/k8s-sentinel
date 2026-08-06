# path: tests/conftest.py  (aggiunta)
import datetime as dt
from types import SimpleNamespace as NS
from unittest.mock import patch

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
