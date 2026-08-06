# path: k8s_sentinel/tools/get_node_resource_status.py
from typing import Optional
from pydantic import BaseModel
from activegraph.packs import tool
from kubernetes.client.rest import ApiException
from .common import (ToolExecutionError, get_core_v1_api, get_custom_objects_api, to_iso)

class Input(BaseModel):
    node_name: Optional[str] = None

class Output(BaseModel):
    nodes: list
    metadata: dict

def _cpu(v):
    if v is None: return None
    s = str(v)
    try:
        if s.endswith("n"): return float(s[:-1]) / 1e9
        if s.endswith("m"): return float(s[:-1]) / 1000
        return float(s)
    except ValueError: return None

def _mem(v):
    if v is None: return None
    s = str(v); units = {"Ki":1024,"Mi":1024**2,"Gi":1024**3,"K":1e3,"M":1e6,"G":1e9}
    for suf, mul in units.items():
        if s.endswith(suf):
            try: return float(s[:-len(suf)]) * mul
            except ValueError: return None
    try: return float(s)
    except ValueError: return None

@tool(name="get_node_resource_status",
      description="Retrieve node conditions and optional metrics (CPU/memory).",
      input_schema=Input, output_schema=Output)
def get_node_resource_status(args: Input, ctx) -> Output:
    core = get_core_v1_api()
    try:
        nodes = ([core.read_node(name=args.node_name)] if args.node_name
                 else core.list_node(timeout_seconds=5).items[:20])
    except ApiException as e:
        raise ToolExecutionError(f"K8s API error: {e.status} {e.reason}") from e
    metrics = {}
    try:
        m = get_custom_objects_api().list_cluster_custom_object(
            "metrics.k8s.io", "v1beta1", "nodes")
        metrics = {i["metadata"]["name"]: i.get("usage", {}) for i in m.get("items", [])}
    except Exception:
        metrics = {}
    out = []
    for n in nodes:
        cap = n.status.capacity or {}
        use = metrics.get(n.metadata.name, {})
        cu, mu = _cpu(use.get("cpu")), _mem(use.get("memory"))
        cc, mc = _cpu(cap.get("cpu")), _mem(cap.get("memory"))
        out.append({"name": n.metadata.name, "unschedulable": n.spec.unschedulable,
                    "conditions": [{"type": c.type, "reason": c.reason}
                                   for c in (n.status.conditions or []) if c.status == "True"],
                    "cpu_percent": round(cu/cc*100, 2) if cu and cc else None,
                    "memory_percent": round(mu/mc*100, 2) if mu and mc else None})
    return Output(nodes=out, metadata={"count": len(out),
                                       "metrics_available": bool(metrics)})
