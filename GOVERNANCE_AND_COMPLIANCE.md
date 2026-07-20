# GOVERNANCE_AND_COMPLIANCE

Operating rules for the 9-phase governance pipeline (ARCHITECTURE.md, AUDIT_PIPELINE.md).

## 1. Zero data egress

- Regulated inputs (dataset samples, processing activity descriptions, findings, evidence)
  never leave the deployment boundary.
- The Redis event fabric is internal-only; webhook "delivery" is a fan-out to the internal
  `governance_events` ledger — no calls to public endpoints exist in the governance code paths.
- Robustness testing (Phase 6) uses **local, deterministic test corpora**; no prompt or payload
  is sent to any external LLM endpoint.
- The default `docker-compose.yml` configuration performs no external network calls at runtime.
- JSON-LD contexts referenced by issued credentials are bundled in `/schemas` and are never
  dereferenced over the network.

## 2. Regulatory coverage (article-level)

| Framework | Articles/Clauses enforced by the pipeline |
|---|---|
| EU AI Act (Reg. 2024/1689) | Art. 5, 6 (+Annex III), 10, 11, 12, 13, 14, 15, 50, 72 |
| GDPR (Reg. 2016/679) | Art. 5, 6, 9, 22, 25, 30, 32, 35, 44–49 |
| India DPDP Act 2023 | Sec. 5, 6, 8, 10, 11–13, 16 |
| NIST AI RMF (AI 100-1) | GOVERN 1.2, MAP 1.1, MEASURE 2.2, 2.7, 3.3, MANAGE 4.1 |
| ISO/IEC 42001:2023 | Clauses 6.1, 7.4.3, 7.5, 8.1.3, 8.2, 9.1 |

Traceability rule: every finding, blocker and certificate claim carries
`{framework, article}` + an `evidenceId` resolving to a Postgres JSONB record and an
`EvidenceArtifact` graph node.

## 3. Least-privilege roles and scopes

Authentication: client-credentials service accounts → HS256 JWT
(`POST /api/v1/auth/token`, claims: `sub`, `role`, `scopes[]`, `exp`). The TypeScript MCP layer
checks the token's scopes against the tool's required scope **before** invoking FastAPI; the
orchestrator re-verifies signature + scope on every request.

| Role | Scopes |
|---|---|
| `governance-admin` | all scopes |
| `intake-officer` | `phase:intake`, `phase:scope`, `runs:read` |
| `audit-engineer` | `phase:risk`, `phase:privacy`, `phase:fairness`, `phase:robustness`, `phase:explainability`, `runs:read` |
| `certification-officer` | `phase:certify`, `phase:monitor`, `reaudit:trigger`, `runs:read`, `certs:read` |

Tool → scope mapping: AUDIT_PIPELINE.md (per phase). Demo client secrets are configured via
`.env` (`GOV_*_SECRET`) and must be rotated for any non-local deployment.

## 4. Deterministic gating & blocker policy

- Blockers are computed by pure, deterministic engine functions: same input + same control
  version ⇒ same output ⇒ same integrity hash.
- A blocker in any phase immediately: marks the phase `blocked`, marks the run `blocked`,
  raises `RemediationTask` nodes in Neo4j, emits a `phase.blocked` event, and permanently
  prevents certificate issuance for that run. Remediation requires a new run (or a reaudit
  after the underlying facts change).

## 5. Cryptographic integrity & non-repudiation

- Certificates: W3C VC 2.0, `DataIntegrityProof` / `eddsa-jcs-2022` / Ed25519,
  `proofPurpose: assertionMethod`, verifiable offline against
  `schemas/w3c_audit_credential.jsonld` and the issuer `did:key`.
- Evidence: per-run SHA-256 hash chain over immutable JSONB records (ARCHITECTURE.md §4.2).
- Events: deterministic event IDs (`SHA-256(runId:phase:integrityHash)`), idempotent consumers,
  dead-letter ledger for unresolved faults.
- Certificate lifecycle is state-versioned: `active → superseded | revoked`; revocations record
  timestamp + reason; the public status endpoint serves as the internal revocation registry.
- Signing keys are generated inside the boundary (`CERT_KEY_FILE`, or the `cert-signer`
  service volume) and are never exported.

## 6. Reaudit governance

Reaudit triggers (model version change, dataset revision, policy/legal baseline update,
critical incident, drift threshold breach) are honored per the impact matrix
(AUDIT_PIPELINE.md §11). Superseded credentials remain queryable for audit history; revoked
credentials fail verification with `revoked` status. All reaudit decisions (impact scope,
diffs, certificate action) are themselves persisted as evidence.
