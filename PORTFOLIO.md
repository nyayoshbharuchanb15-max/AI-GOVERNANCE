# AI Governance MCP Server — Technical Portfolio

**Author:** Nyayosh Bharuchanb15-Max  
**Repository:** https://github.com/nyayoshbharuchanb15-max/AI-GOVERNANCE  
**Version:** 2.0.0

---

## Overview

An on-premise AI compliance auditing system that interfaces with any MCP-compatible AI assistant to perform comprehensive 9-phase audits against the EU AI Act, NIST AI RMF, ISO/IEC 42001, GDPR, and India DPDP Act 2023. Every audit score and regulatory mapping is returned in plain language.

## Technical Highlights

### Real Fairlearn Integration
The bias engine calls actual `fairlearn.metrics` — `demographic_parity_difference`, `equal_opportunity_difference`, `disparate_impact_ratio` — with genuine statistical computation, not simulation.

### W3C Verifiable Credential Pipeline
Full Ed25519 signing with multibase base58btc encoding, `did:key` verification methods, canonicalized payload signing per VC Data Model 1.1, and dual PostgreSQL storage.

### Multi-Regulatory Cross-Mapping
Every audit response carries explicit article/section references to 5 regulatory frameworks including India's DPDP Act 2023 (Sec. 5–14) — coverage most commercial compliance tools lack.

### Merkle Audit Trail
SHA-256 binary Merkle tree with proof generation, verification, and chained `AuditChain` — tamper-evident integrity beyond a simple hash column.

### Data Discovery Crawler
Proactive filesystem scanner for ML model artifacts (.onnx, .pb, .pt, .h5) and datasets (.csv, .parquet, .jsonl) with SHA-256 hashing and automatic Neo4j provenance graph population.

### BLOCKER FAIL Propagation
Sequential phase dependency model where a single critical finding (e.g., missing kill-switch) halts the entire certification pipeline — mirrors real audit workflows.

## Architecture

```
┌──────────────────────┐     ┌──────────────────────────────────────────────┐
│   AI Assistant       │     │         AI Governance MCP Server             │
│  (Claude Desktop,    │◄───►│                                              │
│   Cursor, etc.)      │     │  TypeScript MCP Server        Python Backend │
│                      │     │  ┌──────────────────┐     ┌───────────────┐  │
│  OAuth 2.1 + RBAC ───┤     │  │ 11 MCP Tools      │────►│ FastAPI        │  │
│  PII Middleware ─────┤     │  │ (Risk, Bias,      │     │ (Audit Logic)  │  │
│  Rate Limiting ──────┤     │  │  DPIA, Drift...)  │     │               │  │
│                      │     │  └──────────────────┘     └───────┬───────┘  │
│  Zero Egress ────────┤     └─────────┼─────────────────────────┼──────────┘
│  On-Premise ─────────┤               │       Data Layer        │          │
│                      │  ┌────────────┼─────────────────────────┼──────────┐
│                      │  │            ▼                         ▼          │
│                      │  │ ┌──────────────┐ ┌──────────────┐ ┌─────────┐  │
│                      │  │ │  PostgreSQL  │ │    Neo4j     │ │  Redis  │  │
│                      │  │ │  Evidence    │ │  Provenance  │ │ Streams │  │
│                      │  │ │  Store +     │ │  Graph +     │ │(Re-audit│  │
│                      │  │ │  Merkle Tree │ │  Discovery   │ │ Events) │  │
│                      │  │ └──────────────┘ └──────────────┘ └─────────┘  │
│                      │  └────────────────────────────────────────────────┘
└──────────────────────┘
```

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **TypeScript MCP + Python Backend** | MCP SDK is TypeScript-native; Python is the ML ecosystem standard |
| **PostgreSQL JSONB** | Schema-flexible evidence store for evolving regulatory requirements |
| **Neo4j for Provenance** | Supply chain audit is fundamentally a graph problem |
| **Redis Streams** | Async re-audit triggers without coupling drift detection to execution |
| **Merkle Tree** | Tamper-evident audit trail without blockchain overhead |
| **Dual Transport** | stdio (Claude Desktop) + SSE (web clients) for maximum compatibility |

## Implementation Stack

| Component | Technology | Purpose |
|---|---|---|
| MCP Server | TypeScript + @modelcontextprotocol/sdk | 11 audit tools via MCP protocol |
| Backend | Python + FastAPI | All ML/audit logic |
| Evidence Store | PostgreSQL 16 + asyncpg | JSONB audit evidence with Merkle tree |
| Provenance Graph | Neo4j 5 + async driver | Supply chain lineage tracking |
| Drift Engine | Redis 7 + Streams | Async re-audit triggers |
| Auth | OAuth 2.1 + JWT (RS256) | Scoped RBAC (admin/auditor/viewer) |
| PII Protection | Regex + field-level middleware | Zero-trust data minimization |
| Signing | Ed25519 + multibase base58btc | W3C VC-JSON certificates |
| Bias | Fairlearn + sklearn | Demographic parity, disparate impact |
| Drift | Evidently AI | PSI, KS test, embedding drift |
| CI/CD | GitHub Actions | Python lint+test, TS build, Docker build |
| Database Migrations | Alembic | Versioned schema management |

## File Count

~56 source files, ~7,000 lines of code across:
- 11 FastAPI routers (9 audit phases + auth + DPDP + ROPA + DSAR)
- 12 service modules (bias, drift, crypto, discovery, erasure, etc.)
- 5 middleware modules (PII, rate limit, request ID, body size, auth)
- 11 MCP tool definitions with JSON Schema
- 7 test files (pytest + pytest-asyncio)
- 1 CI/CD pipeline
- 1 Docker Compose stack (5 services)
