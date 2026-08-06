# path: k8s_sentinel/tools/send_ops_alert.py
"""Notifiche ops: Slack + PagerDuty, con auto-escalation P1."""
import os
from typing import Optional, List

import requests
from pydantic import BaseModel, Field
from activegraph.packs import tool

from .common import ToolExecutionError, ToolInputError

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
PAGERDUTY_KEY = os.getenv("PAGERDUTY_INTEGRATION_KEY")


class Input(BaseModel):
    anomaly_id: str
    severity: str
    entity_type: str
    entity_name: str
    namespace: str
    anomaly_type: str
    root_cause_summary: str
    evidence: List[str] = Field(default_factory=list)
    remediation_action: str
    remediation_reasoning: str
    approval_status: str = "pending"
    channels: List[str] = Field(default_factory=lambda: ["slack"])
    inspect_url: Optional[str] = None


class Output(BaseModel):
    delivered: dict
    errors: list


def _slack(data):
    if not SLACK_WEBHOOK_URL:
        raise ToolExecutionError("SLACK_WEBHOOK_URL not set")
    blocks = [
        {"type": "header", "text": {"type": "plain_text",
         "text": f"🚨 K8s Sentinel [{data['severity']}]"}},
        {"type": "section", "text": {"type": "mrkdwn",
         "text": (f"*Anomaly:* `{data['anomaly_id']}`\n*Entity:* "
                  f"`{data['entity_name']}`\n*Root cause:* "
                  f"{data['root_cause_summary']}\n*Remediation:* "
                  f"{data['remediation_action']}")}},
    ]
    if data.get("inspect_url"):
        blocks.append({"type": "context", "elements": [
            {"type": "mrkdwn",
             "text": f"🔍 <{data['inspect_url']}|Inspect full investigation trace>"}]})
    r = requests.post(SLACK_WEBHOOK_URL, json={"blocks": blocks}, timeout=10)
    r.raise_for_status()
    return {"channel": "slack", "status": "sent"}


def _pagerduty(data):
    if not PAGERDUTY_KEY:
        raise ToolExecutionError("PAGERDUTY_INTEGRATION_KEY not set")
    sev = {"P1": "critical", "P2": "error", "P3": "warning"}.get(data["severity"], "info")
    r = requests.post("https://events.pagerduty.com/v2/enqueue",
                      json={"routing_key": PAGERDUTY_KEY, "event_action": "trigger",
                            "dedup_key": f"k8s-sentinel-{data['anomaly_id']}",
                            "payload": {"summary": data["root_cause_summary"],
                                        "severity": sev, "source": data["namespace"]}},
                      timeout=10)
    r.raise_for_status()
    return {"channel": "pagerduty", "status": "sent"}


@tool(name="send_ops_alert",
      description="Send an operations alert to Slack and/or PagerDuty.",
      input_schema=Input, output_schema=Output)
def send_ops_alert(args: Input, ctx) -> Output:
    if args.severity not in ("P1", "P2", "P3"):
        raise ToolInputError(f"Invalid severity {args.severity}")
    data = args.model_dump()
    channels = list(args.channels)
    if args.severity == "P1" and "pagerduty" not in channels:
        channels.append("pagerduty")
    delivered, errors = {}, []
    for ch in channels:
        try:
            if ch == "slack":
                delivered[ch] = _slack(data)
            elif ch == "pagerduty":
                delivered[ch] = _pagerduty(data)
            else:
                raise ToolInputError(f"Unsupported channel {ch}")
        except Exception as e:
            errors.append({"channel": ch, "error": str(e)})
    return Output(delivered=delivered, errors=errors)
