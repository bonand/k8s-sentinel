# path: tests/test_llm_investigator.py
def test_produces_anomaly_and_proposal(runtime, oom_goal, patch_read_only_tools, mock_llm):
    runtime.graph.add_object("GoalRequest", oom_goal, actor="test")
    runtime.run_until_idle()
    assert len(list(runtime.graph.objects(type="Anomaly"))) == 1
    assert len(list(runtime.pending_approvals())) == 1
    # La Remediation NON esiste prima dell'approvazione
    assert len(list(runtime.graph.objects(type="Remediation"))) == 0
