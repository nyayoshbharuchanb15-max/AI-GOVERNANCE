-- Governance pipeline schema (9-phase orchestrated flow) — idempotent.
-- See ARCHITECTURE.md §4.2.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS governance_runs (
    run_id          UUID PRIMARY KEY,
    model_id        VARCHAR(255) NOT NULL,
    model_version   VARCHAR(255) NOT NULL,
    status          VARCHAR(50)  NOT NULL DEFAULT 'in_progress',
    -- in_progress | blocked | certified | monitoring_active | superseded
    reaudit_of      UUID REFERENCES governance_runs(run_id),
    trigger         JSONB,
    context         JSONB NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_gov_runs_model ON governance_runs (model_id);
CREATE INDEX IF NOT EXISTS idx_gov_runs_status ON governance_runs (status);

CREATE TABLE IF NOT EXISTS governance_phase_results (
    result_id       UUID PRIMARY KEY,
    run_id          UUID NOT NULL REFERENCES governance_runs(run_id),
    phase_key       VARCHAR(50)  NOT NULL,
    phase_number    INTEGER      NOT NULL,
    status          VARCHAR(50)  NOT NULL,             -- passed | blocked
    inputs          JSONB NOT NULL,
    outputs         JSONB NOT NULL,
    legal_mappings  JSONB NOT NULL DEFAULT '[]'::jsonb,
    blocker_reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    control_version VARCHAR(100) NOT NULL,
    integrity_hash  VARCHAR(100) NOT NULL,
    prev_hash       VARCHAR(100) NOT NULL,
    evidence_id     UUID NOT NULL,
    carried_forward BOOLEAN NOT NULL DEFAULT FALSE,
    origin_run_id   UUID,
    actor           VARCHAR(255) NOT NULL DEFAULT 'system',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (run_id, phase_key)
);
CREATE INDEX IF NOT EXISTS idx_gov_phase_run ON governance_phase_results (run_id);
CREATE INDEX IF NOT EXISTS idx_gov_phase_payload_gin ON governance_phase_results USING GIN (outputs);

CREATE TABLE IF NOT EXISTS governance_certificates (
    certificate_id  VARCHAR(255) PRIMARY KEY,          -- urn:uuid:…
    run_id          UUID NOT NULL REFERENCES governance_runs(run_id),
    model_id        VARCHAR(255) NOT NULL,
    vc_payload      JSONB NOT NULL,
    status          VARCHAR(50) NOT NULL DEFAULT 'active',
    -- active | superseded | revoked
    supersedes      VARCHAR(255),
    superseded_by   VARCHAR(255),
    revocation_reason TEXT,
    anchor_hash     VARCHAR(100) NOT NULL,
    verification_method TEXT NOT NULL,
    issued_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ,
    revoked_at      TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_gov_cert_model ON governance_certificates (model_id);
CREATE INDEX IF NOT EXISTS idx_gov_cert_status ON governance_certificates (status);

CREATE TABLE IF NOT EXISTS governance_events (
    event_id        VARCHAR(100) PRIMARY KEY,
    stream          VARCHAR(100) NOT NULL,
    event_type      VARCHAR(100) NOT NULL,
    run_id          UUID,
    phase_key       VARCHAR(50),
    payload         JSONB NOT NULL,
    status          VARCHAR(50) NOT NULL DEFAULT 'delivered',
    -- delivered | dead_letter
    attempts        INTEGER NOT NULL DEFAULT 1,
    last_error      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_gov_events_run ON governance_events (run_id);
CREATE INDEX IF NOT EXISTS idx_gov_events_status ON governance_events (status);

CREATE TABLE IF NOT EXISTS governance_monitoring (
    config_id       UUID PRIMARY KEY,
    run_id          UUID NOT NULL REFERENCES governance_runs(run_id),
    model_id        VARCHAR(255) NOT NULL,
    config          JSONB NOT NULL,
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_gov_monitoring_model ON governance_monitoring (model_id);
