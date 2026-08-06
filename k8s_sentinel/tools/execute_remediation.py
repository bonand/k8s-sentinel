# path: k8s_sentinel/tools/execute_remediation.py
import os
from typing import Literal
from pydantic import BaseModel
from activegraph.packs import tool
from kubernetes.client.rest import ApiException
from .common import (ToolExecutionError, ToolInputError, get_apps_v1_api,
                     get_core_v1_api, validate_namespace, validate_pod_name)

EXECUTION_ENABLED = os.getenv("K8S_SENTINEL_EXECUTION_ENABLED", "false").lower() == "true"
ALLOWED_NS = [n for n in os.getenv("K8S_SENTINEL_ALLOWED_NAMESPACES", "").split(",") if n]
ALLOWED_ACTIONS = {"delete_pod", "scale_deployment", "restart_deployment"}

class Input(BaseModel):
    action: Literal["delete_pod", "scale_deployment", "restart_deployment"]
    namespace: str
    target_name: str
    replicas: int = 1
    dry_run: bool = True

class Output(BaseModel):
    action: str
    target: str
    dry_run: bool
    status: str

def _gate(ns, action):
    if not EXECUTION_ENABLED:
        raise ToolExecutionError("Execution disabled (kill-switch)")
    if action not in ALLOWED_ACTIONS:
        raise ToolInputError(f"Action {action} not whitelisted")
    if ALLOWED_NS and ns not in ALLOWED_NS:
        raise ToolInputError(f"Namespace {ns} not whitelisted")

@tool(name="execute_remediation",
      description="Execute an approved remediation (whitelist-gated, dry-run by default).",
      input_schema=Input, output_schema=Output)
def execute_remediation(args: Input, ctx) -> Output:
    _gate(args.namespace, args.action)
    ns = validate_namespace(args.namespace)
    target = f"{ns}/{args.target_name}"
    dry = "All" if args.dry_run else None
    try:
        if args.action == "delete_pod":
            validate_pod_name(args.target_name)
            get_core_v1_api().delete_namespaced_pod(
                name=args.target_name, namespace=ns, dry_run=dry, _request_timeout=10)
            status = "dry_run_ok" if args.dry_run else "deleted"
        elif args.action == "scale_deployment":
            if not 0 <= args.replicas <= 20: raise ToolInputError("replicas out of bounds")
            get_apps_v1_api().patch_namespaced_deployment_scale(
                name=args.target_name, namespace=ns,
                body={"spec": {"replicas": args.replicas}}, dry_run=dry, _request_timeout=10)
            status = "dry_run_ok" if args.dry_run else "scaled"
        else:
            import datetime as dt
            get_apps_v1_api().patch_namespaced_deployment(
                name=args.target_name, namespace=ns,
                body={"spec": {"template": {"metadata": {"annotations":
                      {"kubectl.kubernetes.io/restartedAt":
                       dt.datetime.now(dt.timezone.utc).isoformat()}}}}},
                dry_run=dry, _request_timeout=10)
            status = "dry_run_ok" if args.dry_run else "rolling_restart_triggered"
    except ApiException as e:
        raise ToolExecutionError(f"K8s error: {e.status} {e.reason}") from e
    return Output(action=args.action, target=target, dry_run=args.dry_run, status=status)
