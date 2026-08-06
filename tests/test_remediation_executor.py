# path: tests/test_remediation_executor.py
from unittest.mock import patch

def test_approval_executes(runtime, oom_goal, oom_events, mock_llm):
    with patch("k8s_sentinel.tools.query_cluster_events.query_cluster_events",
               return_value=oom_events), \
         patch("k8s_sentinel.tools.send_ops_alert.send_ops_alert",
               return_value={"delivered": {}, "errors": []}), \
         patch("k8s_sentinel.tools.execute_remediation.execute_remediation",
               return_value={"action": "restart_deployment", "target": "x",
                             "dry_run": False, "status": "rolling_restart_triggered"}):
        runtime.graph.add_object("GoalRequest", oom_goal, actor="test")
        runtime.run_until_idle()
        pending = list(runtime.pending_approvals())
        runtime.approve(pending[0].id, approved_by="tester")
        runtime.run_until_idle()
    rems = list(runtime.graph.objects(type="Remediation"))
    assert len(rems) == 1
