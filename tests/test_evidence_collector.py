# path: tests/test_evidence_collector.py
from unittest.mock import patch

def test_creates_investigation(runtime, oom_goal, oom_events):
    with patch("k8s_sentinel.tools.query_cluster_events.query_cluster_events",
               return_value=oom_events):
        runtime.graph.add_object("GoalRequest", oom_goal, actor="test")
        runtime.run_until_idle()
    assert len(list(runtime.graph.objects(type="Investigation"))) == 1
    assert len(list(runtime.graph.objects(type="ContextFact"))) == 1
    assert [e for e in runtime.graph.events if e.type == "evidence.collected"]

def test_dedup(runtime, oom_goal, oom_events):
    with patch("k8s_sentinel.tools.query_cluster_events.query_cluster_events",
               return_value=oom_events):
        runtime.graph.add_object("GoalRequest", oom_goal, actor="test")
        runtime.run_until_idle()
        runtime.graph.add_object("GoalRequest", oom_goal, actor="test")
        runtime.run_until_idle()
    assert len(list(runtime.graph.objects(type="Investigation"))) == 1
