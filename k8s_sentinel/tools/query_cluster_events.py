# path: k8s_sentinel/tools/query_cluster_events.py
from typing import Optional
from pydantic import BaseModel
from activegraph.packs import tool
from kubernetes.client.rest import ApiException
from .common import (ToolExecutionError, cutoff_minutes, get_core_v1_api,
                     sanitize, to_iso, validate_namespace, validate_pod_name,
                     validate_positive_int)

class Input(BaseModel):
    namespace: Optional[str] = None
    pod_name: Optional[str] = None
    include_normal: bool = False
    since_minutes: int = 15
    limit: int = 50

class Output(BaseModel):
    events: list
    metadata: dict

@tool(name="query_cluster_events",
      description="Retrieve recent Kubernetes events for a namespace or pod.",
      input_schema=Input, output_schema=Output)
def query_cluster_events(args: Input, ctx) -> Output:
    ns = validate_namespace(args.namespace) if args.namespace else None
    pod = validate_pod_name(args.pod_name) if args.pod_name else None
    since = validate_positive_int(args.since_minutes, "since_minutes", 15, 240)
    limit = validate_positive_int(args.limit, "limit", 50, 100)
    core = get_core_v1_api(); cutoff = cutoff_minutes(since)
    try:
        resp = (core.list_namespaced_event(namespace=ns, timeout_seconds=5)
                if ns else core.list_event_for_all_namespaces(timeout_seconds=5))
    except ApiException as e:
        raise ToolExecutionError(f"K8s API error: {e.status} {e.reason}") from e
    events = []
    for ev in resp.items:
        last = ev.last_timestamp or ev.event_time or ev.metadata.creation_timestamp
        if last is None or last < cutoff: continue
        if pod and ev.involved_object.name != pod: continue
        if not args.include_normal and ev.type == "Normal": continue
        events.append({"type": ev.type, "reason": ev.reason,
                       "message": sanitize(ev.message),
                       "object_kind": ev.involved_object.kind,
                       "object_name": ev.involved_object.name,
                       "object_namespace": ev.involved_object.namespace,
                       "count": ev.count, "last_timestamp": to_iso(last)})
    events.sort(key=lambda x: x.get("last_timestamp") or "", reverse=True)
    truncated = len(events) > limit
    return Output(events=events[:limit],
                  metadata={"count": len(events), "truncated": truncated,
                            "cutoff": to_iso(cutoff)})
