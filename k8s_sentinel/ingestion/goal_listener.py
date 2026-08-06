# path: k8s_sentinel/ingestion/goal_listener.py
"""HTTP ingestion: writes GoalRequest objects onto the graph."""
import logging
from fastapi import FastAPI, Request

logger = logging.getLogger(__name__)

class GoalListener:
    def __init__(self, runtime):
        self.runtime = runtime
        self.app = FastAPI(title="K8s Sentinel Ingestion")
        self._routes()

    def _routes(self):
        rt = self.runtime
        @self.app.get("/healthz")
        async def healthz(): return {"status": "ok", "run_id": rt.run_id}

        @self.app.post("/goal")
        async def goal(request: Request):
            b = await request.json()
            rt.graph.add_object("GoalRequest", {
                "kind": "anomaly", "incident_id": b.get("incident_id"),
                "namespace": b.get("namespace"), "pod_name": b.get("pod_name"),
                "deployment": b.get("deployment"),
                "anomaly_type": b.get("anomaly_type", "Unknown"),
                "severity": b.get("severity", "P3"),
                "source": b.get("source", "external-filter"),
                "timestamp": b.get("timestamp"), "log_hint": b.get("log_hint")},
                actor="ingestion.http")
            rt.run_until_idle(); rt.save_state()
            return {"status": "processed"}

        @self.app.get("/pending-approvals")
        async def pending():
            return [{"id": p.id, "reason": p.reason} for p in rt.pending_approvals()]

        @self.app.post("/approve/{approval_id}")
        async def approve(approval_id: str, approved_by: str = "operator"):
            rt.approve(approval_id, approved_by=approved_by)
            rt.run_until_idle(); rt.save_state()
            return {"status": "approved", "id": approval_id}
