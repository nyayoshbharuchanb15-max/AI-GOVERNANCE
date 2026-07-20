# AUDIT_PIPELINE — 9-Phase AI Audit Pipeline

Source of truth for every phase's **tool contract, inputs, outputs and regulatory triggers**.
Each phase is a distinct MCP tool (TypeScript, `/mcp-server/src/governance-tools.ts`) and a
FastAPI route (`/orchestrator`). Dependency ordering per ARCHITECTURE.md §5.

Common response envelope (every phase):

```json
{
  "runId": "…", "phase": "…", "phaseNumber": 1,
  "status": "passed | blocked",
  "controlVersion": "CTRL-<phase>@1.0.0",
  "integrityHash": "sha256:…", "prevHash": "sha256:…",
  "evidenceId": "…",
  "legalMappings": [{ "framework": "…", "article": "…", "title": "…" }],
  "blockers": [{ "code": "…", "framework": "…", "article": "…", "reason": "…", "remediation": "…" }],
  "outputs": { … },
  "completedAt": "ISO-8601"
}
```

Every phase, on completion: (a) writes an immutable JSONB record to Postgres
(inputs, outputs, deterministic integrity hash — ARCHITECTURE.md §4.2), (b) writes lineage
nodes/edges to Neo4j (§4.1), (c) emits an ordered, idempotent event on
`governance:phase-events` (dead-letter on unresolved faults).

Required scope per tool is listed as **Scope**. Roles → scopes: GOVERNANCE_AND_COMPLIANCE.md §3.

---

## Phase 1 — Intake & Context Registration

- **Tool:** `intake_register` · **Route:** `POST /api/v1/phases/intake` · **Scope:** `phase:intake`
- **Regulatory triggers:** EU AI Act Art. 11 (technical documentation); GDPR Art. 30 (records of
  processing activities); ISO/IEC 42001 Clause 7.5 (documented information); NIST AI RMF MAP 1.1.
- **Inputs:**
  - `modelId` (string, `^[a-zA-Z0-9][a-zA-Z0-9._-]*$`), `modelVersion` (string), `ownerTeam` (string)
  - `deploymentContext`: `{ sector, regions[] (e.g. ["EU","IN"]), autonomyLevel: assistive|supervised|autonomous, description? }`
  - `processingActivities[]`: `{ name, purpose, dataCategories[], dataSubjects[], crossBorder (bool), specialCategories[]? }`
  - `datasets[]`: `{ datasetId, version, containsPersonalData (bool), name?, specialCategories[]? }`
- **Outputs:** `{ modelId, modelVersion, registeredActivities[] (activityIds), registeredDatasets[], contextSummary }`
- **Blockers:** none (registration phase). Creates the `AuditRun`, `Model`, `Dataset`,
  `ProcessingActivity` graph nodes.

## Phase 2 — Regulatory Scope Mapping

- **Tool:** `map_regulatory_scope` · **Route:** `POST /api/v1/phases/scope` · **Scope:** `phase:scope`
- **Regulatory triggers:** determines applicability of EU AI Act, GDPR, DPDP Act, NIST AI RMF,
  ISO/IEC 42001 from intake context (regions, personal data, special categories, cross-border,
  autonomy level).
- **Inputs:** `{ runId }`
- **Outputs:** `{ frameworks[], scopeMap[]: { framework, article, title, trigger } }`
  — each entry states *why* the article applies (article-level traceability). Writes
  `(:ProcessingActivity)-[:GOVERNED_BY]->(:RegulatoryArticle)` edges.
- **Blockers:** none.

## Phase 3 — Risk Classification

- **Tool:** `classify_risk` · **Route:** `POST /api/v1/phases/risk` · **Scope:** `phase:risk` · **Engine:** `engines/risk_engine.py`
- **Regulatory triggers:** EU AI Act Art. 5 (prohibited practices), Art. 6 + Annex III
  (high-risk classification), Art. 50 (transparency/limited risk); NIST AI RMF MAP 1.1.
- **Inputs:** `{ runId, riskInputs: { usesRealtimeBiometricId, usesSocialScoring,
  usesManipulativeTechniques, isSafetyComponent, annexIIICategories[]
  (biometric_identification | critical_infrastructure | education | employment |
  essential_services | law_enforcement | migration_border | justice_democracy),
  interactsWithHumans, generatesSyntheticContent } }` (all booleans default false)
- **Outputs:** `{ riskTier: prohibited|high|limited|minimal, rationale[], applicableArticles[] }`.
  The risk tier is persisted to run context and gates phases 4 and 7.
- **Blockers:** `PROHIBITED_PRACTICE` — any Art. 5 practice (social scoring, real-time remote
  biometric identification, manipulative techniques) ⇒ tier `prohibited`, run blocked.

## Phase 4 — Data Protection & Privacy Checks

- **Tool:** `check_data_protection` · **Route:** `POST /api/v1/phases/data-protection` · **Scope:** `phase:privacy` · **Engine:** `engines/privacy_engine.py`
- **Regulatory triggers:** GDPR Art. 5, 6, 9, 22, 25, 30, 35, 44–49; DPDP Act Sec. 5, 6, 8, 10,
  11–13, 16 (when India in scope).
- **Inputs:** `{ runId, dataProtection: { processesPersonalData, lawfulBasis (consent|contract|
  legal_obligation|vital_interests|public_task|legitimate_interests|none), specialCategoryBasis
  (explicit_consent|employment_law|vital_interests|substantial_public_interest|health|none),
  dpiaConducted, dpoAppointed, consentMechanism, crossBorderTransfers[]:
  { destination, mechanism (adequacy_decision|scc|bcr|none) }, retentionPeriodDays,
  dataMinimisationApplied, privacyByDesign } }`
- **Outputs:** `{ findings[]: { check, framework, article, status pass|warning|fail, detail },
  summary: { passed, warnings, failed } }`
- **Blockers:**
  - `NO_LAWFUL_BASIS` — personal data processed with `lawfulBasis: none` (GDPR Art. 6)
  - `SPECIAL_CATEGORY_NO_BASIS` — special categories without an Art. 9(2) basis (GDPR Art. 9)
  - `UNLAWFUL_TRANSFER` — cross-border transfer with `mechanism: none` (GDPR Art. 44–49)
  - `DPIA_MISSING_HIGH_RISK` — high-risk tier without a DPIA (GDPR Art. 35)
  - `DPDP_NO_CONSENT` — India in scope, personal data, no consent mechanism (DPDP Sec. 6)

## Phase 5 — Fairness & Bias Evaluation

- **Tool:** `evaluate_fairness` · **Route:** `POST /api/v1/phases/fairness` · **Scope:** `phase:fairness` · **Engine:** `engines/fairness_engine.py`
- **Regulatory triggers:** EU AI Act Art. 10(2)(f)–(g) (bias examination in data governance);
  GDPR Art. 5(1)(a) (fairness); NIST AI RMF MEASURE 2.2.
- **Inputs:** `{ runId, datasetSample[]: { attributes: {name: value}, outcome (0|1), label? (0|1) },
  sensitiveFeatures[], fairnessThreshold (0–1, default 0.8) }`
- **Outputs:** `{ metrics: { <feature>: { demographicParityDifference, disparateImpactRatio,
  equalOpportunityDifference|null, groupSelectionRates } }, worstDisparateImpact, threshold }`
  (metrics computed deterministically from the provided sample; no data leaves the boundary)
- **Blockers:** `DISPARATE_IMPACT` — disparate impact ratio below `fairnessThreshold`
  (four-fifths rule) for any sensitive feature (EU AI Act Art. 10, GDPR Art. 5(1)(a)).

## Phase 6 — Robustness, Security & Resilience

- **Tool:** `test_robustness` · **Route:** `POST /api/v1/phases/robustness` · **Scope:** `phase:robustness` · **Engine:** `engines/robustness_engine.py`
- **Regulatory triggers:** EU AI Act Art. 15 (accuracy, robustness, cybersecurity);
  NIST AI RMF MEASURE 2.7; ISO/IEC 42001 Clause 8.1.3.
- **Inputs:** `{ runId, testSuites[] (prompt_injection | jailbreak | data_extraction | evasion |
  poisoning_resilience), securityControls: { inputSanitization, outputFiltering, rateLimiting,
  adversarialTraining, anomalyMonitoring, accessControl } }`
- **Outputs:** `{ suites[]: { suite, totalCases, passed, failed, resistanceScore, severity,
  failedCases[] }, overallResistance, vulnerabilities[] }`. Test corpora are local and
  deterministic: a case passes iff all controls it requires are declared; identical inputs and
  control version reproduce identical outputs. No prompts are sent to any external endpoint.
- **Blockers:** `CRITICAL_VULNERABILITY` — `prompt_injection` or `jailbreak` resistance score
  < 0.5 (EU AI Act Art. 15(5)).

## Phase 7 — Explainability & Human Oversight

- **Tool:** `verify_explainability` · **Route:** `POST /api/v1/phases/explainability` · **Scope:** `phase:explainability` · **Engine:** `engines/explainability_engine.py`
- **Regulatory triggers:** EU AI Act Art. 13 (transparency to deployers), Art. 14 (human
  oversight), Art. 12 (record-keeping), Art. 86 (right to explanation); GDPR Art. 22.
- **Inputs:** `{ runId, oversight: { hasHumanInTheLoop, hasKillSwitch,
  overrideProcedureDocumented, oversightRoles[] }, explainability: { method (shap | lime |
  integrated_gradients | attention_maps | rule_based | none), userFacingExplanations,
  decisionLogsRetained, logRetentionDays } }`
- **Outputs:** `{ oversightScore (0–100), findings[] }`
- **Blockers (high-risk tier only):**
  - `NO_KILL_SWITCH` — Art. 14(4)(e) requires an intervention/stop capability for **all**
    high-risk systems
  - `NO_HUMAN_OVERSIGHT` — no human-in-the-loop and no documented override (Art. 14)
  - `NO_EXPLAINABILITY` — `method: none` for a high-risk system (Art. 13, Art. 86)
  - `NO_DECISION_LOGS` — decision logs not retained (Art. 12)

## Phase 8 — Certification Assembly (VC 2.0)

- **Tool:** `assemble_certification` · **Route:** `POST /api/v1/phases/certification` · **Scope:** `phase:certify`
- **Regulatory triggers:** ISO/IEC 42001 Clause 9.1; EU AI Act Art. 43 (conformity assessment
  analogue); W3C VC Data Model 2.0.
- **Preconditions (hard gate):** phases 4–7 all `passed`; no blocker anywhere in the run.
  A blocked run returns `409 CERTIFICATION_BLOCKED` — deterministic, no override.
- **Inputs:** `{ runId, issuer: { name, contact? }, validityDays (default 365) }`
- **Outputs:** `{ certificateId, credential (full signed VC 2.0 per
  schemas/w3c_audit_credential.jsonld), verification: { verified, verificationMethod,
  cryptosuite } }` — the credential is verified immediately after signing before being returned.
- **Blockers:** issuance itself introduces none; the gate above rejects blocked runs.

## Phase 9 — Continuous Monitoring & Reaudit Triggering

- **Tool:** `configure_monitoring` · **Route:** `POST /api/v1/phases/monitoring` · **Scope:** `phase:monitor`
- **Regulatory triggers:** EU AI Act Art. 72 (post-market monitoring), Art. 15; ISO/IEC 42001
  Clause 9.1; NIST AI RMF MEASURE 3.3 / MANAGE 4.1.
- **Inputs:** `{ runId, monitors: { driftThreshold (default 0.2), fairnessDriftThreshold
  (default 0.1), reauditTriggers[] (default: all five trigger types) } }`
- **Outputs:** `{ monitoringConfigId, armedTriggers[], eventStream: "governance:reaudit" }`.
  Run status becomes `monitoring_active`. Production observations are submitted to
  `POST /api/v1/monitoring/observe`; threshold breaches publish a reaudit trigger event.
- **Blockers:** none.

---

## 10. Auxiliary tools & routes

| Tool | Route | Scope |
|---|---|---|
| `trigger_reaudit` | `POST /api/v1/reaudit` | `reaudit:trigger` |
| `get_audit_run` | `GET /api/v1/runs/{runId}` | `runs:read` |
| — | `GET /api/v1/runs/{runId}/lineage` | `runs:read` |
| — | `GET /api/v1/certificates/{id}` | `certs:read` |
| — | `GET /api/v1/certificates/{id}/verify` | public (read-only) |
| — | `GET /api/v1/certificates/{id}/status` | public (read-only) |
| — | `POST /api/v1/monitoring/observe` | `phase:monitor` |
| — | `GET /api/v1/events/recent`, `GET /api/v1/events/dead-letter` | `runs:read` |
| — | `POST /api/v1/auth/token` | public (client credentials) |

`trigger_reaudit` inputs: `{ modelId, trigger: { type (model_version_change | dataset_revision |
policy_update | critical_incident | drift_threshold_breach), detail, datasetId?,
newModelVersion?, policyReference?, updatedPhaseInputs? (map phase → revised inputs, e.g. the
revised dataset sample for a dataset_revision) } }`

`trigger_reaudit` outputs: `{ reauditRunId, previousRunId, impactScope: { trigger,
impactedPhases[], dependentPhases[], carriedForwardPhases[], affectedGraphNodes[] },
findingsDiff[], certificateAction: { action (reissued | revoked | blocked_no_reissue),
previousCertificateId, newCertificateId? } }`

## 11. Reaudit impact matrix

| Trigger | Impacted phases (re-run) | Dependent (always re-run) |
|---|---|---|
| `model_version_change` | risk, fairness, robustness, explainability | certification, monitoring |
| `dataset_revision` | data_protection, fairness | certification, monitoring |
| `policy_update` | scope, risk, data_protection | certification, monitoring |
| `critical_incident` | robustness, explainability | certification, monitoring |
| `drift_threshold_breach` | fairness, robustness | certification, monitoring |

All other phases are carried forward (original integrity hashes retained,
`carried_forward = true`, origin run referenced). Re-runs execute against the stored immutable
inputs of the previous run, plus any trigger deltas (`newModelVersion`, `updatedPhaseInputs`).
Old vs new findings are diffed per phase; the certificate is re-issued/superseded/revoked per
ARCHITECTURE.md §7.
