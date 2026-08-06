# path: tests/test_remediation_executor.py
def test_approval_executes(runtime, oom_goal, patch_read_only_tools, mock_llm):
    runtime.graph.add_object("GoalRequest", oom_goal, actor="test")
    runtime.run_until_idle()
    pending = list(runtime.pending_approvals())
    assert pending
    runtime.approve(pending[0].id, approved_by="tester")
    runtime.run_until_idle()
    rems = list(runtime.graph.objects(type="Remediation"))
    assert len(rems) == 1
    assert rems[0].data["status"] == "executed"
