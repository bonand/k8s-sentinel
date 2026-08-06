# path: dashboard/main.py
"""Read-only inspection UI backend."""
import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from activegraph import Runtime
from activegraph.store import open_store

STORE = os.getenv("ACTIVEGRAPH_STORE_URL", "sqlite:///data/sentinel.db")

app = FastAPI(title="K8s Sentinel Dashboard")
app.mount("/static", StaticFiles(directory="static"), name="static")


def _latest_run_id():
    """Prende l'ultimo run dallo store (ordinato per creazione)."""
    store = open_store(STORE)
    runs = list(store.list_runs())
    if not runs:
        return None
    # list_runs restituisce in ordine cronologico; prendiamo l'ultimo
    return runs[-1].id if hasattr(runs[-1], 'id') else runs[-1]


def _rt():
    """Carica il runtime con l'ultimo run disponibile."""
    run_id = _latest_run_id()
    if run_id is None:
        raise HTTPException(503, "No runs in store yet. Trigger an investigation first.")
    return Runtime.load(STORE, run_id=run_id)


@app.get("/api/investigations")
def investigations(limit: int = 50):
    """Lista delle investigation recenti."""
    rt = _rt()
    items = [{"id": o.id, "external_id": o.data.get("external_id"),
              "status": o.data.get("status"), "severity": o.data.get("severity"),
              "anomaly_type": o.data.get("anomaly_type"), "opened_at": o.data.get("opened_at")}
             for o in rt.graph.objects(type="Investigation")]
    items.sort(key=lambda x: x.get("opened_at") or "", reverse=True)
    return items[:limit]


@app.get("/api/investigation/{iid}/graph")
def investigation_graph(iid: str):
    """Ritorna il grafo completo di una investigation (nodi + archi)."""
    rt = _rt()
    if not rt.graph.get_object(iid):
        raise HTTPException(404, "Investigation not found")
    nodes, edges, seen, queue = [], [], set(), [iid]
    while queue:
        nid = queue.pop(0)
        if nid in seen:
            continue
        seen.add(nid)
        obj = rt.graph.get_object(nid)
        if not obj:
            continue
        nodes.append({"id": obj.id, "type": obj.type, "data": obj.data})
        for rel in rt.graph.relations(source=nid):
            edges.append({"source": rel.source, "target": rel.target, "type": rel.type})
            queue.append(rel.target)
        for rel in rt.graph.relations(target=nid):
            edges.append({"source": rel.source, "target": rel.target, "type": rel.type})
            queue.append(rel.source)
    return {"nodes": nodes, "edges": edges}


@app.get("/api/investigation/{iid}/trace")
def investigation_trace(iid: str):
    """Audit trail completo: tutti gli eventi causalmente collegati."""
    rt = _rt()
    if not rt.graph.get_object(iid):
        raise HTTPException(404, "Investigation not found")
    events = [{"id": e.id, "type": e.type, "timestamp": e.timestamp,
               "actor": e.actor, "payload": e.payload}
              for e in rt.graph.events]
    return events


@app.get("/", response_class=HTMLResponse)
def root():
    """Serve l'interfaccia web."""
    with open("static/index.html") as f:
        return f.read()
