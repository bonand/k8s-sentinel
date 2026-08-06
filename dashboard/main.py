# path: dashboard/main.py
"""Read-only inspection UI backend."""
import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from activegraph import Runtime

STORE = os.getenv("ACTIVEGRAPH_STORE_URL", "sqlite:///data/sentinel.db")
RUN_ID = os.getenv("ACTIVEGRAPH_RUN_ID", "k8s-sentinel-dev")
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

def _rt(): return Runtime.load(STORE, run_id=RUN_ID)

@app.get("/api/investigations")
def investigations(limit: int = 50):
    rt = _rt()
    items = [{"id": o.id, "external_id": o.data.get("external_id"),
              "status": o.data.get("status"), "severity": o.data.get("severity"),
              "anomaly_type": o.data.get("anomaly_type"), "opened_at": o.data.get("opened_at")}
             for o in rt.graph.objects(type="Investigation")]
    items.sort(key=lambda x: x.get("opened_at") or "", reverse=True)
    return items[:limit]

@app.get("/api/investigation/{iid}/graph")
def graph(iid: str):
    rt = _rt()
    if not rt.graph.get_object(iid): raise HTTPException(404)
    nodes, edges, seen, queue = [], [], set(), [iid]
    while queue:
        nid = queue.pop(0)
        if nid in seen: continue
        seen.add(nid); obj = rt.graph.get_object(nid)
        if not obj: continue
        nodes.append({"id": obj.id, "type": obj.type, "data": obj.data})
        for rel in rt.graph.relations(source=nid):
            edges.append({"source": rel.source, "target": rel.target, "type": rel.type})
            queue.append(rel.target)
        for rel in rt.graph.relations(target=nid):
            edges.append({"source": rel.source, "target": rel.target, "type": rel.type})
            queue.append(rel.source)
    return {"nodes": nodes, "edges": edges}

@app.get("/", response_class=HTMLResponse)
def root():
    with open("static/index.html") as f: return f.read()
