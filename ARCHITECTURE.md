# ARCHITECTURE — AI Governance MCP Server

This document is the **source of truth** for the 9-phase governance pipeline. Where any
implementation detail is ambiguous, this document prevails.

## 1. Product summary

The AI Governance MCP Server is an **on-premise compliance orchestration service** exposing a
9-phase AI audit pipeline to MCP-compatible AI assistants. It produces auditable, article-level
evidence of conformance with the **EU AI Act (Reg. 2024/1689)**, **GDPR (Reg. 2016/679)**,
**NIST AI RMF (AI 100-1)**, **ISO/IEC 42001:2023**, and **India's DPDP Act 2023**, and issues
**W3C Verifiable Credential 2.0** certification artifacts. No regulated data may leave the
deployment boundary.

> The repository also ships the original ComplianceStack 17-tool suite (`/python-backend`).
> The 9-phase governance pipeline described here is the orchestrated, dependency-gated
> certification flow layered on the same infrastructure (PostgreSQL, Neo4j, Redis).

## 2. Stack (fixed — do not substitute)

| Layer | Technology | Responsibility | Location |
|---|---|---|---|
| MCP interface + API façade | TypeScript | MCP tool contracts, request schema validation, policy-gated endpoints, request hashing | `/mcp-server` |
| Governance orchestration | FastAPI (Python) | Workflow routing, phase execution control, deterministic state transitions | `/orchestrator` |
| Audit/analysis engines | Python | Risk analysis, fairness checks, robustness/security testing, explainability scans | `/engines` |
| Event/webhook fabric | Redis Streams | Async tasking, evidence event fan-out, idempotent retry-safe webhook delivery, dead-letter routing | `/events` |
| Graph persistence | Neo4j | Control graph lineage (see §4.1) | `/graph` |
| Relational persistence | PostgreSQL (JSONB) | Immutable phase inputs/outputs, fairness metrics, validation reports, legal mappings, blocker reasons | `/store` |
| Certificate store | Signed credential store | W3C VC 2.0 payloads, proof metadata, issuance/revocation status | `/certs` + `governance_certificates` table |

## 3. Component flow

```
MCP-Compatible AI Assistant
  → TypeScript API Layer            (/mcp-server: schema validation, authz, request hashing)
  → FastAPI Orchestration Engine    (/orchestrator: phase state, dependency preconditions, sequencing)
  → Redis Webhook Engine            (/events: async jobs, idempotent retries, event envelopes) → Postgres
  → Python Audit Engines            (/engines: risk / fairness / robustness / explainability)
  → Neo4j Control Graph (/graph) + PostgreSQL JSONB Evidence Store (/store)
  → Certificate Store               (/certs: VC 2.0 + cryptographic proof)
```

Every hop is a real, callable interface:

1. **TypeScript layer** validates each tool call against a strict JSON Schema
   (`additionalProperties: false`), enforces role-scoped authorization by inspecting the scopes
   of the configured service-account JWT, and computes an `X-Request-Hash`
   (SHA-256 over the canonical JSON body). Malformed or unauthorized requests are rejected
   **before** the FastAPI orchestrator is invoked.
2. **FastAPI orchestrator** re-verifies the JWT signature and scope, re-verifies the request
   hash when present, enforces phase ordering (§5), executes the phase, persists evidence, writes
   lineage, and emits an event.
3. **Redis fabric** carries `governance:phase-events` (phase completions),
   `governance:reaudit` (reaudit triggers) and `governance:dead-letter` (unresolved faults).
   Delivery is consumer-group based, idempotent (deterministic event IDs + processed-set dedupe)
   and retry-safe (pending-claim redelivery; ≥3 failed attempts → dead-letter).
4. **Certificate signing** is performed by the `/certs` layer — embedded in the orchestrator
   process, or as the dedicated `cert-signer` service in Docker Compose
   (`CERT_SIGNER_URL`). Keys never leave the deployment boundary.

## 4. Persistence model

### 4.1 Neo4j control graph lineage

Node labels:

| Label | Key property | Meaning |
|---|---|---|
| `Model` | `modelId` (+ `version`) | AI system under audit |
| `Dataset` | `datasetId` (+ `version`) | Training/eval data |
| `ProcessingActivity` | `activityId` | GDPR Art. 30-style processing activity |
| `RegulatoryArticle` | `articleId` (e.g. `EU-AI-ACT:Art.14`) | Article-level legal reference |
| `Control` | `controlId` (+ `version`) | Technical control executed by a phase |
| `TestExecution` | `executionId` | One execution of a control within a run |
| `EvidenceArtifact` | `evidenceId` (+ `integrityHash`) | Postgres JSONB evidence record |
| `AuditRun` | `runId` | One pipeline run (initial or reaudit) |
| `PhaseResult` | `resultId` (+ `phase`, `status`) | Outcome of one phase in a run |
| `RemediationTask` | `taskId` | Task raised for a blocker/failed finding |
| `Certificate` | `certificateId` (+ `status`) | Issued VC 2.0 credential |

Relationships:

```
(Model)-[:PERFORMS]->(ProcessingActivity)
(Model)-[:TRAINED_ON]->(Dataset)
(ProcessingActivity)-[:GOVERNED_BY]->(RegulatoryArticle)
(Control)-[:SATISFIES]->(RegulatoryArticle)
(Control)-[:VERIFIED_BY]->(TestExecution)
(TestExecution)-[:PRODUCED]->(EvidenceArtifact)
(AuditRun)-[:AUDITS]->(Model)
(AuditRun)-[:INCLUDES]->(PhaseResult)
(PhaseResult)-[:EXECUTED]->(TestExecution)
(PhaseResult)-[:RAISED]->(RemediationTask)
(AuditRun)-[:CERTIFIED_BY]->(Certificate)
(AuditRun)-[:REAUDIT_OF]->(AuditRun)
```

This yields the three documented lineage chains:
`Model → ProcessingActivity → RegulatoryArticle`,
`Control → TestExecution → EvidenceArtifact`, and
`AuditRun → PhaseResult → RemediationTask`.

### 4.2 PostgreSQL JSONB evidence store

Migration: `store/migrations/002_governance.sql` (idempotent). Tables:

| Table | Purpose |
|---|---|
| `governance_runs` | run id, model id/version, status, reaudit lineage (`reaudit_of`), trigger, full intake context (JSONB) |
| `governance_phase_results` | one immutable record per phase per run: `inputs` JSONB, `outputs` JSONB, `legal_mappings` JSONB, `blocker_reasons` JSONB, `control_version`, `integrity_hash`, `prev_hash`, `evidence_id`, `carried_forward` |
| `governance_certificates` | full VC 2.0 payload (JSONB), proof metadata, `status` (`active`/`superseded`/`revoked`), supersession links, `anchor_hash` |
| `governance_events` | delivered/dead-lettered event envelopes (webhook delivery ledger) |
| `governance_monitoring` | armed monitoring configuration per certified run |

**Integrity hashing.** Every phase record carries
`integrity_hash = SHA-256(canonical_json({run_id, phase, control_version, inputs, outputs, prev_hash}))`
where `prev_hash` is the integrity hash of the previous phase record in the run
(`SHA-256(run_id)` for the intake phase). Records are therefore hash-linked to the run ID and
form a per-run hash chain. Deterministic gating: **same inputs + same control version ⇒ same
outputs ⇒ same integrity hash**. Timestamps are stored alongside but never hashed.

## 5. Phase state machine

Phases and dependency preconditions (a phase cannot run until every prerequisite phase has
**passed** in the same run):

```
1 intake            ← (none)
2 scope             ← intake
3 risk              ← scope
4 data_protection   ← risk
5 fairness          ← risk
6 robustness        ← risk
7 explainability    ← risk
8 certification     ← data_protection ∧ fairness ∧ robustness ∧ explainability
9 monitoring        ← certification
```

Run statuses: `in_progress → blocked | certified → monitoring_active → superseded`.

Rules (deterministic gating):

- A phase may execute **at most once** per run (`409 PHASE_ALREADY_EXECUTED`).
- Missing prerequisite ⇒ `409 PRECONDITION_NOT_MET` listing the missing phases.
- A **blocker finding in any phase** sets the phase status to `blocked`, sets the run status to
  `blocked`, halts the pipeline (every subsequent phase call returns `409 RUN_BLOCKED`) and
  **prevents certificate issuance** (`409 CERTIFICATION_BLOCKED`).
- Re-execution never mutates prior records; reaudits create a **new run** (§7).

## 6. Certification (W3C VC 2.0)

- Context: `https://www.w3.org/ns/credentials/v2` + the repository schema
  `schemas/w3c_audit_credential.jsonld` (bundled locally — never fetched at runtime).
- Proof: `DataIntegrityProof` with cryptosuite `eddsa-jcs-2022`
  (JCS/RFC 8785 canonicalization + Ed25519), `proofPurpose: assertionMethod`,
  `verificationMethod` = `did:key` derived from the Ed25519 public key
  (multicodec `0xed01`, base58btc multibase).
- The credential subject embeds the run ID, risk tier, per-phase integrity hashes, evidence IDs
  and article-level legal references — every technical claim maps to an article and an evidence ID.
- Non-repudiation: the stored certificate row carries `anchor_hash = SHA-256(canonical VC)`;
  issuance/supersession/revocation are state-versioned rows, never overwrites.
- Verification: `GET /api/v1/certificates/{id}/verify` (public, read-only) re-canonicalizes and
  verifies the Ed25519 proof, expiry, revocation status and schema shape. A verifier holding only
  the credential JSON and the issuer public key can verify independently offline.

## 7. Reaudit pattern (Impact Scope Resolver)

Trigger types: `model_version_change`, `dataset_revision`, `policy_update`,
`critical_incident`, `drift_threshold_breach`.

Flow: trigger (API `POST /api/v1/reaudit` or `governance:reaudit` event from monitoring)
→ resolve affected Neo4j nodes (model, datasets, controls, evidence)
→ compute impacted phases from the impact matrix (AUDIT_PIPELINE.md §11)
→ create a new run (`reaudit_of` = previous run), carry forward unaffected phase results
(original integrity hashes retained, `carried_forward = true`)
→ re-run only impacted phases + dependent phases (certification, monitoring) using the stored
immutable inputs of the previous run
→ diff old vs new findings per phase
→ certificate action: all pass ⇒ **re-issue** (new credential supersedes old; old marked
`superseded`); any blocker ⇒ **revoke** the active credential and block the run.

## 8. Security constraints (non-negotiable)

1. **No external data egress** — regulated inputs and evidence never leave the deployment
   boundary; the event fabric is internal-only; no code path performs outbound calls with
   regulated payloads; the default Compose network is a private bridge with no public endpoints.
2. **Least privilege** — every phase tool is role-scoped (GOVERNANCE_AND_COMPLIANCE.md §3);
   the TypeScript layer enforces authorization before FastAPI is invoked; FastAPI re-enforces.
3. **Cryptographic integrity** — all certificate outputs are signed and independently
   verifiable (§6).
4. **Deterministic gating** — §5.
5. **Traceability** — every technical claim maps to an article-level legal reference and an
   evidence ID (`legal_mappings` JSONB + `RegulatoryArticle` nodes).
6. **Non-repudiation** — §6 anchoring + hash-chained, timestamped, state-versioned records.

## 9. Deployment

- `docker compose up --build -d` brings up: `mcp-server` (TypeScript), `orchestrator` (FastAPI,
  port 8010), `cert-signer` (port 8020, internal), `python-backend` (legacy 17-tool suite),
  `postgres`, `neo4j`, `redis` — all on a private bridge network, no external calls.
- Environment configuration: `.env.example` (governance section).
- End-to-end proof: `pytest tests/e2e/test_governance_pipeline.py` runs a sample model through
  all 9 phases, produces a signed VC 2.0 certificate, exercises the blocker gate, ordering
  enforcement, least-privilege rejection, the reaudit flow and dead-letter routing.
