# path: k8s_sentinel/tools/get_deployment_history.py
from typing import Optional
from pydantic import BaseModel
from activegraph.packs import tool
from kubernetes.client.rest import ApiException
from .common import (ToolExecutionError, cutoff_minutes, get_apps_v1_api,
                     to_iso, validate_namespace, validate_positive_int)

class Input(BaseModel):
    namespace: str
    deployment: Optional[str] = None
    since_minutes: int = 60
    limit: int = 20

class Output(BaseModel):
    deployments: list
    replica_sets: list
    metadata: dict

@tool(name="get_deployment_history",
      description="Retrieve recent deployments and ReplicaSets for rollout correlation.",
      input_schema=Input, output_schema=Output)
def get_deployment_history(args: Input, ctx) -> Output:
    ns = validate_namespace(args.namespace)
    since = validate_positive_int(args.since_minutes, "since_minutes", 60, 1440)
    apps = get_apps_v1_api(); cutoff = cutoff_minutes(since)
    try:
        deps = apps.list_namespaced_deployment(namespace=ns, timeout_seconds=5)
        rss = apps.list_namespaced_replica_set(namespace=ns, timeout_seconds=5)
    except ApiException as e:
        raise ToolExecutionError(f"K8s API error: {e.status} {e.reason}") from e
    uid2name = {}; deployments = []
    for d in deps.items:
        if args.deployment and d.metadata.name != args.deployment: continue
        uid2name[d.metadata.uid] = d.metadata.name
        deployments.append({"name": d.metadata.name, "replicas": d.spec.replicas,
                            "ready_replicas": d.status.ready_replicas,
                            "created_at": to_iso(d.metadata.creation_timestamp)})
    replica_sets = []
    for rs in rss.items:
        owner = next((o for o in (rs.metadata.owner_references or [])
                      if o.kind == "Deployment"), None)
        if not owner or owner.uid not in uid2name: continue
        created = rs.metadata.creation_timestamp
        if created and created < cutoff: continue
        rev = (rs.metadata.annotations or {}).get("deployment.kubernetes.io/revision")
        replica_sets.append({"name": rs.metadata.name,
                             "deployment": uid2name[owner.uid],
                             "revision": int(rev) if rev else None,
                             "images": [c.image for c in rs.spec.template.spec.containers],
                             "created_at": to_iso(created)})
    replica_sets.sort(key=lambda x: x.get("revision") or 0, reverse=True)
    return Output(deployments=deployments[:args.limit],
                  replica_sets=replica_sets[:args.limit],
                  metadata={"namespace": ns, "cutoff": to_iso(cutoff)})
