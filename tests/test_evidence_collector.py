# path: tests/test_evidence_collector.py
def test_creates_investigation(runtime, oom_goal, patch_read_only_tools, mock_llm):
    runtime.graph.add_object("GoalRequest", oom_goal, actor="test")
    runtime.run_until_idle()
    assert len(list(runtime.graph.objects(type="Investigation"))) == 1
    assert len(list(runtime.graph.objects(type="ContextFact"))) == 1
    assert [e for e in runtime.graph.events if e.type == "evidence.collected"]


def test_dedup(runtime, oom_goal, patch_read_only_tools, mock_llm):
    runtime.graph.add_object("GoalRequest", oom_goal, actor="test")
    runtime.run_until_idle()
    runtime.graph.add_object("GoalRequest", oom_goal, actor="test")
    runtime.run_until_idle()
    assert len(list(runtime.graph.objects(type="Investigation"))) == 1
    assert [e for e in runtime.graph.events if e.type == "investigation.deduplicated"]
