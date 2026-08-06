# path: tests/test_llm_investigator.py
from unittest.mock import patch

def test_produces_anomaly_and_proposal(runtime, oom_goal, oom_events, mock_llm):
    with patch("k8s_sentinel.tools.query_cluster_events.query_cluster_events",
               return_value=oom_events), \
         patch("k8s_sentinel.tools.send_ops_alert.send_ops_alert",
               return_value={"delivered": {"slack": {"status": "sent"}}, "errors": []}):
        runtime.graph.add_object("GoalRequest", oom_goal, actor="test")
        runtime.run_until_idle()
    assert len(list(runtime.graph.objects(type="Anomaly"))) == 1
    assert len(list(runtime.pending_approvals())) == 1
    # Remediation NON esiste prima dell'approvazione
    assert len(list(runtime.graph.objects(type="Remediation"))) == 0
