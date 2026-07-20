# Deployment guide — AI Governance MCP Server

This guide describes how to deploy the AI Governance MCP Server in a **fully
on-premise / air-gapped** environment (the target deployment mode — no outbound
API calls are permitted for regulated workflows).

All state is kept in three local databases: PostgreSQL (evidence store),
Neo4j (control-graph lineage) and Redis (event fabric).

---

## 1. Deployment options

| Mode | Best for | How |
|------|----------|-----|
| **Docker Compose** | Production, staging, on-prem | `docker compose up -d` — bundles all six services on a single host. |
| **Kubernetes (manifest)** | Multi-tenant, HA | Adapt the compose file into a Helm chart; each service is a stateless Deployment (except the DBs). |
| **Bare metal / apt** | Air-gapped labs (current preview) | Install PostgreSQL, Neo4j, Redis natively; run the orchestrator via `uvicorn`/`supervisor` and the MCP server via `node`. |

The preview pod uses the bare-metal mode (see `PRD.md`).

---

## 2. Prerequisites

- Linux host (tested on Debian 12 / Ubuntu 22.04)
- Docker Engine ≥ 24 + Docker Compose plugin (for the compose flow)
- OR: PostgreSQL ≥ 14, Neo4j ≥ 5, Redis ≥ 5, Python ≥ 3.11, Node ≥ 20 (for the bare-metal flow)
- Outbound network is **not required**. All Python + Node dependencies must be
  vendored beforehand in air-gapped environments (see § 6).

---

## 3. Docker Compose (recommended)

```bash
git clone <this repo> ai-governance && cd ai-governance

# 1. Generate a production-ready .env with fresh 32-byte secrets.
#    The orchestrator refuses to boot with weak/unset values.
bash scripts/gen-secrets.sh > .env
chmod 600 .env

# 2. (Optional) Edit .env to set GOVERNANCE_PUBLIC_BASE_URL, MCP_ALLOWED_ORIGINS,
#    CORS_ORIGINS, HIDE_GOOGLE_SIGNIN, etc.

# 3. Pre-seed the Ed25519 signer key (once).
docker volume create cert-keys
docker run --rm -v cert-keys:/keys alpine sh -c \
  'dd if=/dev/urandom of=/keys/ed25519.seed bs=32 count=1 && chmod 600 /keys/ed25519.seed'

# 4. Bring the stack up. Postgres/Neo4j/Redis are internal only (no host port).
docker compose up -d --build
docker compose ps
```

The compose stack exposes only two host ports:

| Service          | Container port | Host port | Notes |
|------------------|---------------:|----------:|-------|
| orchestrator     | 8010           | 8010      | FastAPI orchestrator + `/api/v1` |
| mcp-server       | 3000           | 3000      | Auditor Workbench SPA + MCP transport + same-origin `/api/*` proxy → orchestrator |
| cert-signer      | 8020           | *(private)* | Ed25519 VC 2.0 signer |
| postgres         | 5432           | *(private)* | Evidence store |
| neo4j            | 7687           | *(private)* | Bolt / lineage graph |
| redis            | 6379           | *(private)* | Event fabric |

The SPA (`http://localhost:3000/`) makes `/api/v1/*` calls to the mcp-server,
which reverse-proxies them into the `orchestrator` container over the private
`governance-net` network. This means the browser never has to reach port
8010 directly and CORS is a non-issue for same-origin deployments.

### Smoke test

```bash
# 1. Overall health (from the host)
curl -s http://localhost:8010/api/v1/health | jq

# 2. Same health path through the SPA proxy (should match)
curl -s http://localhost:3000/api/v1/health | jq

# 3. Full audit walk via governance-admin service account
source .env
TOKEN=$(curl -s -X POST http://localhost:8010/api/v1/auth/token \
  -H 'Content-Type: application/json' \
  -d "{\"clientId\":\"governance-admin\",\"clientSecret\":\"$GOV_ADMIN_SECRET\"}" \
  | jq -r .accessToken)
curl -s http://localhost:8010/api/v1/runs -H "Authorization: Bearer $TOKEN" | jq .
```

Open the Auditor Workbench at **http://localhost:3000/**. Sign in with a
service-account role card (paste the corresponding `GOV_*_SECRET` from
your `.env`) or click **Sign in with Google** if enabled (see § 4.1).

### Regression test against your compose stack

```bash
export GOVERNANCE_API_URL=http://localhost:8010
export $(grep '^GOV_\|^GOVERNANCE_JWT' .env | xargs)
python -m pytest tests/governance -v
# Expect: 36 passed (28 pipeline/artifacts/gap-analysis + 8 Google Auth)
```

---

## 4. Environment variables

All secrets and connection strings are supplied through environment variables —
no hard-coded fallbacks in the codebase or the compose file. `.env.example`
is the canonical reference; `scripts/gen-secrets.sh` produces a ready-to-use
`.env` with fresh 32-byte secrets for every `KEY=__GENERATE__` line.

Required at boot (orchestrator refuses to start otherwise):

| Env var | Purpose | Generation |
|---|---|---|
| `POSTGRES_PASSWORD` | Postgres superuser | `openssl rand -base64 32` |
| `NEO4J_PASSWORD` | Neo4j auth | `openssl rand -base64 32` |
| `GOVERNANCE_JWT_SECRET` | HS256 signing key | `python3 -c "import secrets;print(secrets.token_urlsafe(32))"` |
| `GOV_ADMIN_SECRET` | governance-admin service account | *(same)* |
| `GOV_INTAKE_SECRET` | intake-officer service account | *(same)* |
| `GOV_AUDIT_SECRET` | audit-engineer service account | *(same)* |
| `GOV_CERT_SECRET` | certification-officer service account | *(same)* |
| `GOVERNANCE_CLIENT_SECRET` | mcp-server → orchestrator (usually `=${GOV_ADMIN_SECRET}`) | *(same)* |

Startup validator (`orchestrator/config.py`) refuses to boot with any of the
old dev-secret strings (`govern-admin-secret-dev`, `intake-officer-secret-dev`,
etc.), empty values, or secrets shorter than 24 characters.

### 4.1 Google Sign-In (Emergent-managed OAuth)

The Auditor Workbench ships a **Sign in with Google** button that uses
Emergent's managed OAuth flow. When a user completes the flow, the
orchestrator mints a governance JWT and an httpOnly `governance_session`
cookie (7-day TTL). Endpoints (all under `/api/v1`):

- `POST /auth/google/session` — exchanges the returned `X-Session-ID` header
  for a governance JWT + cookie
- `GET  /auth/me` — returns the current Google-authenticated user (cookie
  or `Authorization: Bearer <session_token>`)
- `POST /auth/logout` — invalidates the DB session row and clears the cookie

Hosts the flow needs to reach:
- `auth.emergentagent.com` — user-facing OAuth screen
- `demobackend.emergentagent.com` — session-data exchange (backend → backend)

#### 4.1.1 Allow-list (mandatory in production)

By default any Google-authenticated user is minted `governance-admin` — fine
for a demo, unsafe for production. Configure the allow-list via env vars:

```
GOOGLE_ALLOWED_EMAILS=alice@acme.com=governance-admin,bob@acme.com=audit-engineer
GOOGLE_ALLOWED_DOMAINS=acme.com=audit-engineer
```

Rules:
- Exact-email matches take precedence over domain matches.
- The `=role` suffix is optional; omitted → `governance-admin`.
- Valid roles: `governance-admin`, `intake-officer`, `audit-engineer`, `certification-officer`.
- Users not on either list receive `403 GOOGLE_USER_NOT_AUTHORIZED`.

If both lists are empty AND `NODE_ENV=production`, the orchestrator
**refuses to boot**. In development it emits a startup WARNING but
continues (permissive mode).

#### 4.1.2 Hardened air-gapped installs

For deployments that forbid egress, set `HIDE_GOOGLE_SIGNIN=1` in `.env`.
The button is then omitted from the login page entirely (compile-time
injection into `window.__GOV_CONFIG__`), and the backend endpoints
continue to exist but will never be reached from the SPA. All
authentication then goes through the service-account flow.

#### 4.1.3 Testing escape hatch (never in production)

Two-gate guard: `GOV_ALLOW_TEST_AUTH=1` AND `NODE_ENV != production`.
When both hold and a request arrives with
`X-Session-ID: $GOOGLE_AUTH_TEST_SESSION_ID`, the orchestrator returns
a synthetic user (`$GOOGLE_AUTH_TEST_EMAIL`) instead of contacting
Emergent Auth. Boot **refuses** when `NODE_ENV=production` and the flag
is on — that's the SEC-001 safeguard.

### 4.2 Ed25519 signing key

The signer expects a 32-byte seed at `CERT_KEY_FILE`. See Step 3 above for
the pre-seeding command. Back this file up to your HSM / vault — losing it
invalidates all issued certificates.

---

## 5. Database migrations

Migrations are idempotent and run automatically at orchestrator startup. They
live in:

- `/app/store/migrations/*.sql`  — PostgreSQL
- `/app/graph/migrations/*.cypher` — Neo4j

Current PostgreSQL migrations:

| # | File | Purpose |
|---|------|---------|
| 002 | `002_governance.sql` | Core: runs, phase results, certificates, events, monitoring |
| 003 | `003_artifacts.sql` | Evidence artifacts + per-phase article citations |
| 004 | `004_gap_analysis.sql` | Extracted text + document gap findings |
| 005 | `005_google_auth.sql` | Emergent-managed Google Sign-In sessions (httpOnly cookie backing store) |

To force a rerun (e.g. after restoring a backup): drop the corresponding tables
and restart the orchestrator; the migration runner will re-apply any missing
scripts.

---

## 6. Air-gapped / vendored dependencies

Because no outbound egress is allowed:

1. **Python** — vendor wheels once, then install offline:
   ```bash
   pip download -r orchestrator/requirements.txt -d vendor/py
   pip install --no-index --find-links=vendor/py -r orchestrator/requirements.txt
   ```
2. **Node** — commit the `mcp-server/package-lock.json` and use `yarn install --offline` after seeding
   the offline mirror (`yarn config set yarn-offline-mirror ./vendor/node`).
3. **Postgres / Neo4j / Redis** — pin the Docker image digests in `docker-compose.yml`
   and pre-pull them onto the target host.

The MCP server itself embeds no third-party service calls; the entire audit
pipeline runs on-CPU with deterministic engines + local databases.

---

## 7. Backup & restore

The evidence chain and certificates are cryptographically hash-linked; a
consistent snapshot requires a coordinated dump.

```bash
# Postgres
docker compose exec postgres pg_dump -U $POSTGRES_USER -Fc $POSTGRES_DB \
  > backups/evidence_store_$(date +%F).dump

# Neo4j (offline dump)
docker compose stop neo4j
docker compose run --rm neo4j neo4j-admin database dump neo4j \
  --to-path=/backups
docker compose start neo4j

# Redis (RDB snapshot)
docker compose exec redis redis-cli BGSAVE
docker compose cp redis:/data/dump.rdb backups/dump_$(date +%F).rdb

# Ed25519 seed (encrypt at rest)
gpg --symmetric /var/lib/governance/keys/ed25519.seed
```

Restore is the reverse. Because the run/phase/certificate hashes chain into
the Neo4j lineage, all three stores must be restored from the **same snapshot
timestamp** to preserve integrity.

---

## 8. Observability

- `GET /api/v1/health` — overall + per-service status (postgres, neo4j, redis, certSigner).
- `GET /api/v1/events/recent` — recent phase events on the Redis stream.
- `GET /api/v1/events/dead-letter` — poisoned events after 3 delivery attempts.
- Structured logs on stdout (orchestrator + mcp-server). Ship them to your
  SIEM via journald / Fluent Bit — no direct egress from the app.

---

## 9. Rolling upgrades

1. Read the release notes (`memory/PRD.md` + `CHANGELOG.md`) for schema changes.
2. Take a snapshot (§ 7).
3. Deploy the new orchestrator container. Migrations apply automatically.
4. Roll the mcp-server container.
5. Verify: `python -m pytest tests/governance -q` from the same host or run
   the `/api/v1/health` smoke test.

Because every phase output is deterministically hashed and chained, upgrades
that change engine outputs will produce different `integrityHash` values —
you should re-run in-flight audits on the new version and cross-reference
certificates by their `supersedes` link.

---

## 10. Security hardening checklist

- [ ] `.env` generated via `scripts/gen-secrets.sh` (32-byte URL-safe tokens);
      no `KEY=__GENERATE__` line remains.
- [ ] JWT secret ≥ 32 random bytes; rotated quarterly.
- [ ] Service-account passwords rotated on the same cadence.
- [ ] Ed25519 signing seed stored in an HSM / bind-mounted secret, not the repo.
- [ ] MCP `/mcp` endpoint reachable only from trusted network segments.
- [ ] MCP `MCP_ALLOWED_ORIGINS` set to the fully-qualified UI hostname.
- [ ] `CORS_ORIGINS` set to the **exact** SPA origin (never `*`; the
      orchestrator refuses `*` at boot when combined with credentials).
- [ ] `postgres`, `neo4j`, `redis` NOT exposed to any host port — network-namespace only.
- [ ] `HIDE_GOOGLE_SIGNIN=1` **OR** `GOOGLE_ALLOWED_EMAILS`/`GOOGLE_ALLOWED_DOMAINS`
      populated (SEC-002). The orchestrator refuses to boot in production
      if Google Sign-In is enabled with an empty allow-list.
- [ ] `NODE_ENV=production` set — this locks out the Google-Auth testing
      escape hatch (SEC-001) even if `GOV_ALLOW_TEST_AUTH=1` leaks in.
- [ ] `GOV_ALLOW_TEST_AUTH=0` (must be 0 in `.env`).
- [ ] Backup snapshots stored encrypted (age / gpg / KMS).
- [ ] Audit logs (structured JSON) shipped to an append-only SIEM.
- [ ] Regular reaudit trigger cadence configured for each certified model.
