# path: tests/test_ops_alerter.py
from unittest.mock import patch

def test_alert_delivered(runtime, oom_goal, oom_events, mock_llm):
    with patch("k8s_sentinel.tools.query_cluster_events.query_cluster_events",
               return_value=oom_events), \
         patch("k8s_sentinel.tools.send_ops_alert.send_ops_alert",
               return_value={"delivered": {"slack": {"status": "sent"}}, "errors": []}) as m:
        runtime.graph.add_object("GoalRequest", oom_goal, actor="test")
        runtime.run_until_idle()
    assert m.called
    alerts = list(runtime.graph.objects(type="Alert"))
    assert alerts and alerts[0].data["status"] == "delivered"
