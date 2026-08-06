# path: tests/mocks/mock_k8s_api.py
"""Mock K8s API for local docker-compose testing."""
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/api/v1/namespaces/{ns}/events")
@app.get("/api/v1/events")
async def events(ns: str = None):
    return {"items": []}

@app.get("/healthz")
async def healthz(): return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=6443)
