# path: tests/mocks/mock_k8s_api.py
"""Standalone mock Kubernetes API server for manual experimentation.

NOTA: i tool di K8s Sentinel usano kubeconfig/in-cluster config, quindi questo
mock NON è cablato in docker-compose né consumato dai tool. Serve per provare
i tool manualmente puntando un kubeconfig su http://localhost:6443.
"""
from fastapi import FastAPI
import uvicorn

app = FastAPI()


@app.get("/api/v1/namespaces/{ns}/events")
@app.get("/api/v1/events")
async def events(ns: str = None):
    return {"items": []}


@app.get("/apis/apps/v1/namespaces/{ns}/deployments")
async def deployments(ns: str):
    return {"items": []}


@app.get("/api/v1/nodes")
async def nodes():
    return {"items": []}


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=6443)
