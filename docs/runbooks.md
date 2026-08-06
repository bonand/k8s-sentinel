# path: docs/runbooks.md
# K8s Sentinel — Operations Runbooks

Procedures for operating, debugging, and governing the K8s Sentinel agent.
Audience: on-call SREs, platform engineers, agent maintainers.

> **Golden rule:** the agent *investigates and proposes*. Humans *approve and own*
> every state-changing action. When in doubt, do not approve — investigate manually.

---

## 0. Conventions & Prerequisites

**Access required**

- `kubectl` configured for the target cluster
- `activegraph` CLI installed
- Reachability of the agent HTTP API (default `:9000`) and dashboard (default `:8000`)

**Key locations**

| What | Where |
|---|---|
| Event store | `sqlite:///data/sentinel.db` (or `ACTIVEGRAPH_PERSIST_TO`) |
| Agent API | `:9000` — `/healthz`, `/goal`, `/pending-approvals`, `/approve/{id}`, `/reject/{id}` |
| Dashboard | `:8000` |
| Alerts | Slack `#ops-alerts`; PagerDuty (P1 only) |

**Severity model**

| Severity | Meaning | Response |
|---|---|---|
| P1 | Production outage / data-loss risk | Page immediately (PagerDuty auto-escalates) |
| P2 | Degraded service, partial impact | Acknowledge within 15 min |
| P3 | Warning, no user impact | Business hours |

---

## RB-01 — Triage an incoming alert

1. **Read the alert.** Note severity, affected entity, root-cause summary, evidence, proposed remediation.
2. **Open the investigation.** Dashboard → click the investigation, or:
   ```bash
   activegraph inspect sqlite:///data/sentinel.db --tail 50
   ```
3. **Verify independently** (never trust the agent blindly):
   ```bash
   kubectl get events -n <ns> --sort-by=.lastTimestamp | tail -20
   kubectl get pod <pod> -n <ns> -o wide
   kubectl logs <pod> -n <ns> --tail=100
   ```
4. **Decide** using RB-02 (approve / reject / manual fix).
5. **For P1:** join the bridge; treat the agent output as one input among many.

---

## RB-02 — Review, approve, or reject a remediation

**List pending approvals**

```bash
curl -s http://<agent>:9000/pending-approvals | jq .
```

**Review checklist before approving**

- [ ] Root cause matches the evidence (read the `tool.responded` payloads in the trace)
- [ ] Remediation is the least disruptive option that fixes the cause
- [ ] Target namespace is in `K8S_SENTINEL_ALLOWED_NAMESPACES`
- [ ] Blast radius understood (e.g. restart during peak traffic?)

**Approve**

```bash
curl -X POST "http://<agent>:9000/approve/<approval_id>?approved_by=<your-id>"
```

The executor then performs a **dry-run first**, then the real action. Watch:

```bash
activegraph inspect sqlite:///data/sentinel.db --tail 20   # remediation.executed / remediation.failed
```

**Reject**

```bash
curl -X POST "http://<agent>:9000/reject/<approval_id>?denied_by=<your-id>&reason=<why>"
```

The denial is recorded as an `approval.denied` event (who + why), keeping the
audit trail honest. Then resolve the incident manually.

---

## RB-03 — Audit an investigation (post-mortem support)

```bash
# Recent events
activegraph inspect sqlite:///data/sentinel.db --tail 100

# One event in full (payload, actor, caused_by)
activegraph inspect sqlite:///data/sentinel.db --event evt_042

# Prove the run still replays identically
activegraph replay sqlite:///data/sentinel.db --run <run_id> --strict
```

Every `llm.requested` carries a `prompt_hash`; every `tool.responded` carries
the exact data the LLM saw. Use these to answer *"why did the agent think that?"*
and attach the exported trace to the post-mortem.

---

## RB-04 — Agent health & common failures

```bash
curl -s http://<agent>:9000/healthz
kubectl get pod -n k8s-sentinel
```

| Symptom | Likely cause | Action |
|---|---|---|
| `/goal` returns but nothing happens | `run_until_idle` raised | `kubectl logs -n k8s-sentinel <pod>`; look for `behavior.failed` |
| Many `behavior.failed` events | Tool or schema error | Inspect the failing event; fix tool/config; redeploy |
| `runtime.budget_exhausted` event | Too many LLM/tool calls per run | Raise budget or tighten the external log filter |
| `tool.responded` errors (Loki) | Loki unreachable / bad `LOKI_URL` | Verify Loki; agent degrades gracefully (evidence `status=error`) |
| Approvals piling up | No one approving | RB-02; alert on pending count |
| `SchemaVersionMismatch` | Store written by another activegraph version | `activegraph migrate` to a fresh store, or pin the version |

The agent is stateless w.r.t. logic: state lives in the event log. Restarting the
pod is always safe; it reloads and resumes from the log.

---

## RB-05 — Safety controls (kill-switch & scope)

**Disable all write actions (immediate)**

```bash
kubectl set env statefulset/k8s-sentinel -n k8s-sentinel K8S_SENTINEL_EXECUTION_ENABLED=false
kubectl rollout status statefulset/k8s-sentinel -n k8s-sentinel
```

The agent keeps investigating and alerting but cannot execute anything.

**Narrow the blast radius**

```bash
kubectl set env statefulset/k8s-sentinel -n k8s-sentinel K8S_SENTINEL_ALLOWED_NAMESPACES=staging
```

**Full stop**

```bash
kubectl scale statefulset/k8s-sentinel -n k8s-sentinel --replicas=0
```

**Re-enable checklist**

- [ ] Root cause understood
- [ ] Fix validated via fork-and-diff (RB-06)
- [ ] Execution re-enabled in `staging` first, observed ≥ 24h
- [ ] False-positive and approval rates acceptable

---

## RB-06 — The agent made a bad call: improve it safely

1. **Edit the prompt** in your working tree (`k8s_sentinel/prompts.py`).
   With an editable install (`pip install -e .`) no reinstall is needed.
2. **Fork the real incident and re-run with the new prompt:**
   ```bash
   python scripts/improve_prompt.py \
     --store sqlite:///data/sentinel.db \
     --parent-run <run_id> \
     --fork-run experiment-fix-1
   ```
   (Defaults to forking at the first `evidence.collected`; override with `--at-event`.)
3. **Compare diagnoses:**
   ```bash
   activegraph diff sqlite:///data/sentinel.db --run-a <run_id> --run-b experiment-fix-1
   ```
4. Ship the prompt change **only** if the fork demonstrably improves the diagnosis.

---

## RB-07 — A remediation made things worse

1. **Stop the write path** (RB-05, kill-switch).
2. **Roll back manually**, e.g.:
   ```bash
   kubectl rollout undo deployment/<name> -n <ns>
   kubectl scale deployment/<name> -n <ns> --replicas=<previous>
   ```
3. **Preserve evidence:** take a store backup now (RB-08) and do not compact or
   delete the run; it is the provenance for the post-mortem.
4. Reproduce and fix the decision via RB-06 before re-enabling.

---

## RB-08 — Backup & restore of the event store

The agent image has no `sqlite3` CLI; use the Python module instead.

**Backup**

```bash
# 1. Safe online backup inside the pod
kubectl exec -n k8s-sentinel k8s-sentinel-0 -- python -c \
  "import sqlite3; s=sqlite3.connect('/app/data/sentinel.db'); d=sqlite3.connect('/app/data/backup.db'); s.backup(d); d.close(); s.close()"

# 2. Pull it off-cluster (no tar needed)
kubectl exec -n k8s-sentinel k8s-sentinel-0 -- cat /app/data/backup.db > ./sentinel-backup.db
```

**Restore** (agent must be stopped; uses a temporary pod on the same PVC)

```bash
kubectl scale statefulset/k8s-sentinel -n k8s-sentinel --replicas=0

cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata: { name: sentinel-restore, namespace: k8s-sentinel }
spec:
  restartPolicy: Never
  containers:
    - name: restore
      image: python:3.12-slim
      command: ["sh", "-c", "sleep 3600"]
      volumeMounts: [{ name: data, mountPath: /app/data }]
  volumes:
    - name: data
      persistentVolumeClaim: { claimName: data-k8s-sentinel-0 }
EOF

kubectl exec -i -n k8s-sentinel sentinel-restore -- sh -c 'cat > /app/data/sentinel.db' < ./sentinel-backup.db
kubectl delete pod -n k8s-sentinel sentinel-restore
kubectl scale statefulset/k8s-sentinel -n k8s-sentinel --replicas=1
```

For production prefer PostgreSQL (`ACTIVEGRAPH_PERSIST_TO=postgresql://...`)
and your standard DB backup/HA tooling.

---

## Escalation Matrix

| Situation | Escalate to |
|---|---|
| Application incident alert | Service owner (per severity SLA) |
| Agent misdiagnosis (no harm) | Agent maintainers; RB-06 experiment |
| Agent executed a harmful action | **P1** — platform lead + security; RB-07 |
| Store corruption / agent down | Platform on-call; RB-08 |

---

## Appendix — Cheat sheet

```bash
curl -s localhost:9000/healthz                            # liveness
curl -s localhost:9000/pending-approvals | jq             # awaiting approval
curl -X POST localhost:9000/approve/<id>?approved_by=me   # approve
curl -X POST localhost:9000/reject/<id>?denied_by=me&reason=why
activegraph inspect sqlite:///data/sentinel.db --tail 50
activegraph inspect sqlite:///data/sentinel.db --event <evt>
activegraph replay  sqlite:///data/sentinel.db --run <run> --strict
activegraph diff    sqlite:///data/sentinel.db --run-a A --run-b B
```
