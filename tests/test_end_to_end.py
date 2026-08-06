# path: tests/test_end_to_end.py
def test_full_lifecycle(runtime, oom_goal, patch_read_only_tools, mock_llm):
    runtime.graph.add_object("GoalRequest", oom_goal, actor="test")
    runtime.run_until_idle()
    runtime.approve(list(runtime.pending_approvals())[0].id, approved_by="ops")
    runtime.run_until_idle()
    assert list(runtime.graph.objects(type="Investigation"))
    assert list(runtime.graph.objects(type="Anomaly"))
    assert list(runtime.graph.objects(type="Remediation"))
    assert list(runtime.graph.objects(type="Alert"))
