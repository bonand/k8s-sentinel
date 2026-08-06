# path: tests/test_end_to_end.py
from unittest.mock import patch

def test_full_lifecycle(runtime, oom_goal, oom_events, mock_llm):
    with patch("k8s_sentinel.tools.query_cluster_events.query_cluster_events",
               return_value=oom_events), \
         patch("k8s_sentinel.tools.send_ops_alert.send_ops_alert",
               return_value={"delivered": {"slack": {"status": "sent"}}, "errors": []}), \
         patch("k8s_sentinel.tools.execute_remediation.execute_remediation",
               return_value={"action": "restart_deployment", "target": "x",
                             "dry_run": False, "status": "ok"}):
        runtime.graph.add_object("GoalRequest", oom_goal, actor="test")
        runtime.run_until_idle()
        runtime.approve(list(runtime.pending_approvals())[0].id, approved_by="ops")
        runtime.run_until_idle()
    assert list(runtime.graph.objects(type="Investigation"))
    assert list(runtime.graph.objects(type="Anomaly"))
    assert list(runtime.graph.objects(type="Remediation"))
    assert list(runtime.graph.objects(type="Alert"))
