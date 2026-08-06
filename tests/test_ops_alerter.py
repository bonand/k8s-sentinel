# path: tests/test_ops_alerter.py
def test_alert_delivered(runtime, oom_goal, patch_read_only_tools, mock_llm):
    runtime.graph.add_object("GoalRequest", oom_goal, actor="test")
    runtime.run_until_idle()
    alerts = list(runtime.graph.objects(type="Alert"))
    assert alerts and alerts[0].data["status"] == "delivered"
