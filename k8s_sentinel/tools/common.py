# path: k8s_sentinel/tools/common.py
"""Shared helpers: validation, redaction, K8s clients, errors."""
import datetime as dt
import os
import re
from functools import lru_cache
from kubernetes import client, config

MAX_MESSAGE_CHARS = 800

class ToolInputError(ValueError): ...
class ToolExecutionError(RuntimeError): ...

SECRET_PATTERNS = [
    re.compile(r"(?i)bearer\s+[a-z0-9\-._~+/]+=*"),
    re.compile(r"(?i)(api[_-]?key|password|token|secret)\s*[:=]\s*[^\s]+"),
]

def validate_namespace(ns):
    if not ns or not re.match(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$", ns):
        raise ToolInputError(f"Invalid namespace: {ns!r}")
    return ns

def validate_pod_name(name):
    if not name or not re.match(r"^[a-z0-9]([-a-z0-9.]*[a-z0-9])?$", name):
        raise ToolInputError(f"Invalid pod name: {name!r}")
    return name

def validate_positive_int(v, name, default, max_v):
    if v is None: return default
    v = int(v)
    if v <= 0: raise ToolInputError(f"{name} must be > 0")
    return min(v, max_v)

def sanitize(text, limit=MAX_MESSAGE_CHARS):
    if text is None: return None
    text = str(text)
    for p in SECRET_PATTERNS:
        text = p.sub("[REDACTED]", text)
    return text if len(text) <= limit else text[:limit] + "...[truncated]"

def to_iso(ts):
    if ts is None: return None
    if ts.tzinfo is None: ts = ts.replace(tzinfo=dt.timezone.utc)
    return ts.isoformat()

def cutoff_minutes(m):
    return dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=m)

def _load():
    try: config.load_incluster_config()
    except config.ConfigException: config.load_kube_config()

@lru_cache(maxsize=1)
def get_core_v1_api():
    _load(); return client.CoreV1Api()

@lru_cache(maxsize=1)
def get_apps_v1_api():
    _load(); return client.AppsV1Api()

@lru_cache(maxsize=1)
def get_custom_objects_api():
    _load(); return client.CustomObjectsApi()
