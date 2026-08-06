# path: k8s_sentinel/tools/query_service_logs.py
import json, os, time
from typing import Optional
import requests
from pydantic import BaseModel
from activegraph.packs import tool
from .common import (ToolExecutionError, sanitize, to_iso, validate_namespace,
                     validate_pod_name, validate_positive_int)
import datetime as dt

LOKI_URL = os.getenv("LOKI_URL")
LOKI_TOKEN = os.getenv("LOKI_TOKEN")

class Input(BaseModel):
    namespace: str
    pod_name: Optional[str] = None
    container: Optional[str] = None
    since_minutes: int = 10
    contains: Optional[str] = None
    limit: int = 100

class Output(BaseModel):
    logs: list
    metadata: dict

@tool(name="query_service_logs",
      description="Retrieve application logs from Loki for a namespace/pod.",
      input_schema=Input, output_schema=Output)
def query_service_logs(args: Input, ctx) -> Output:
    if not LOKI_URL: raise ToolExecutionError("LOKI_URL not configured")
    ns = validate_namespace(args.namespace)
    pod = validate_pod_name(args.pod_name) if args.pod_name else None
    limit = validate_positive_int(args.limit, "limit", 100, 200)
    sel = [f'namespace="{ns}"']
    if pod: sel.append(f'pod="{pod}"')
    if args.container: sel.append(f'container="{args.container}"')
    logql = "{" + ", ".join(sel) + "}"
    if args.contains: logql += f" |= {json.dumps(args.contains)}"
    end = int(time.time()); start = end - args.since_minutes * 60
    headers = {"Accept": "application/json"}
    if LOKI_TOKEN: headers["Authorization"] = f"Bearer {LOKI_TOKEN}"
    try:
        r = requests.get(f"{LOKI_URL}/loki/api/v1/query_range",
                         params={"query": logql, "start": start, "end": end,
                                 "limit": limit, "direction": "backward"},
                         headers=headers, timeout=10)
        r.raise_for_status(); payload = r.json()
    except requests.RequestException as e:
        raise ToolExecutionError(f"Loki request failed: {e}") from e
    logs = []
    for stream in payload.get("data", {}).get("result", []):
        labels = stream.get("stream", {})
        for ts_ns, line in stream.get("values", []):
            ts = dt.datetime.fromtimestamp(int(ts_ns)/1e9, dt.timezone.utc)
            logs.append({"timestamp": to_iso(ts), "pod": labels.get("pod"),
                         "message": sanitize(line)})
    logs.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
    return Output(logs=logs[:limit], metadata={"logql": logql, "count": len(logs)})
