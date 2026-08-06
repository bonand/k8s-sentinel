# Changelog

All notable changes to K8s Sentinel will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `POST /reject/{approval_id}` endpoint: denial recorded as `approval.denied` with denier and reason
- Fork-and-diff workflow (`scripts/fork_and_diff.py`, `scripts/improve_prompt.py`)
- Dashboard UI for investigation inspection
- Comprehensive test suite with fixtures and replay tests
- Docker deployment manifests (StatefulSet, RBAC, PVC)

### Changed
- Migrated from polling-based ingestion to event-driven HTTP triggers (call-and-drain)
- Tool registration uses the `@tool` decorator; tools are passed to `@llm_behavior(tools=[...])`
- `llm_investigator` now honors `SENTINEL_LLM_MODEL`
- `send_ops_alert` renders `inspect_url` as a Slack context block when provided

### Fixed
- Remediation objects are created only after approval (via `ctx.propose_object`)
- Test suite now mocks at the K8s/HTTP client boundary so `ctx.call` dispatch is intercepted
- `remediation_executor` accepts payload key variants of `approval.granted`
- Deduplication logic for concurrent anomaly triggers
- RBAC permissions scoped to minimum required verbs

### Security
- Global kill-switch for execution (`K8S_SENTINEL_EXECUTION_ENABLED`)
- Namespace whitelist for write operations
- Dry-run by default for all execution tools
- Secret redaction in log retrieval tools

---

## [0.1.0] - 2026-08-06

### Added

#### Core Architecture
- Event-sourced incident investigation pipeline on Active Graph
- Four reactive behaviors: `evidence_collector`, `llm_investigator`, `ops_alerter`, `remediation_executor`
- Seven object types: `GoalRequest`, `Investigation`, `K8sEntity`, `ContextFact`, `Anomaly`, `Remediation`, `Alert`
- Six relation types: `INVESTIGATES`, `HAS_EVIDENCE`, `ABOUT`, `PRODUCED`, `HAS_REMEDIATION`, `TRIGGERED_ALERT`

#### Investigation Tools (read-only)
- `query_cluster_events`, `query_service_logs`, `get_deployment_history`, `get_node_resource_status`

#### Execution Tools (whitelist-gated)
- `execute_remediation` with `delete_pod`, `scale_deployment`, `restart_deployment`;
  dry-run by default, namespace whitelist, global kill-switch

#### Notification Tools
- `send_ops_alert` (Slack blocks + PagerDuty Events API v2, P1 auto-escalation)

#### Ingestion Layer
- FastAPI HTTP server: `POST /goal`, `GET /healthz`, `GET /pending-approvals`, `POST /approve/{id}`

#### Safety Model
- Read-only investigation tools; approval-gated execution; RBAC minimum

#### Testing / Deployment / Docs / Operator Tools
- pytest suite with fixtures and replay tests
- Kubernetes manifests (namespace, RBAC, StatefulSet, dashboard, secrets example)
- README, CONTRIBUTING, architecture doc, runbooks
- `Makefile`, `scripts/`, fork-and-diff utilities

### Security
- Input validation via Pydantic schemas; secret redaction; no tool can modify secrets/configmaps/RBAC

---

## Version History

| Version | Release Date | Status |
|---------|--------------|--------|
| 0.1.0   | 2026-08-06   | Initial release |
