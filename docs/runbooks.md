# path: docs/runbooks.md
# K8s Sentinel — Operations Runbooks

Procedures for operating, debugging, and governing the K8s Sentinel agent.
Audience: on-call SREs, platform engineers, and agent maintainers.

> **Golden rule:** the agent *investigates and proposes*. Humans *approve and own*
> every state-changing action. When in doubt, do not approve — investigate manually.

---

## 0. Conventions & Prerequisites

**Access required**

- `kubectl` configured for the target cluster (read access; write only if you are the approver)
- `activegraph` CLI installed
- Reachability of the agent HTTP API (default `:9000`) and dashboard (default `:8000`)

**Key locations**

| What | Where |
|---|---|
| Event store | `sqlite:///data/sentinel.db` (or `ACTIVEGRAPH_PERSIST_TO`) |
| Agent API | `http://<agent>:9000` (`/healthz`, `/goal`, `/pending-approvals`, `/approve/{id}`) |
| Dashboard | `http://<dashboard>:8000` |
| Alerts | Slack `#ops-alerts`, PagerDuty (P1 only) |

**Severity model**

| Severity | Meaning | Response |
|---|---|---|
| P1 | Production outage / data-loss risk | Page immediately; PagerDuty auto-escalates |
| P2 | Degraded service, partial impact | Acknowledge within 15 min |
| P3 | Warning, no user impact | Handle in business hours |

---

## RB-01 — Triage an incoming alert

1. **Read the alert.** Note severity, affected entity, root-cause summary, evidence list, and the proposed remediation.
2. **Open the investigation.** Dashboard → click the investigation, or:
   ```bash
   activegraph inspect sqlite:///data/sentinel.db --tail 50
