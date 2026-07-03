# Changelog

All notable changes to ComplianceStack will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-07-02

### Added

- **17-Phase Audit Pipeline**: Complete AI compliance auditing across 5 regulatory frameworks
- **MCP Server**: TypeScript implementation with Model Context Protocol SDK
- **Python Backend**: FastAPI services for all audit logic
- **W3C Verifiable Credentials**: Cryptographically signed audit certificates
- **BLOCKER FAIL Mechanism**: Prevents certification of non-compliant models
- **Zero Data Egress Architecture**: All operations in-process, no external API calls
- **OAuth 2.1 + RBAC**: Role-based access control with scoped endpoints
- **Merkle Audit Trail**: Tamper-evident evidence chain
- **PII Redaction Middleware**: Intercepts and redacts PII from API responses
- **Docker Orchestration**: Complete containerized deployment
- **CI/CD Pipeline**: GitHub Actions for testing and deployment

### Regulatory Coverage

- **EU AI Act** (Reg. 2024/1689): Art. 5, 6, 10, 12, 14, 15, Annex I–III
- **NIST AI RMF** (AI 100-1): MAP 1.1, GOVERN 1.2, 3.2, MEASURE 1.3, 2.2, 3.3, 4.1
- **ISO/IEC 42001:2023**: Clauses 6.1, 6.2, 7.4.3, 7.5, 8.1.2, 8.1.3, 8.2, 9.1
- **GDPR** (Reg. 2016/679): Art. 5, 9, 22, 25, 30, 35, 44–49
- **India DPDP Act 2023**: Sec. 5–14

### MCP Tools

1. `classify_ai_risk` - EU AI Act risk tier classification
2. `discover_supply_chain` - Filesystem crawler with Neo4j provenance graph
3. `audit_supply_chain` - Supply chain audit via Neo4j graph queries
4. `verify_human_oversight` - HITL/kill-switch verification
5. `run_bias_assessment` - Fairlearn bias metrics
6. `generate_dpia` - GDPR Art. 35 DPIA generation
7. `run_adversarial_tests` - Prompt injection, jailbreak, OOD testing
8. `score_audit_weighted` - Aggregate scoring with BLOCKER FAIL
9. `generate_audit_certificate` - W3C Verifiable Credential issuance
10. `monitor_model_drift` - Evidently AI drift detection
11. `audit_session_memory` - STM/LTM isolation audit
12. `audit_rag_quality` - RAG pipeline quality evaluation
13. `audit_prompt_templates` - Injection surface assessment
14. `audit_agent_trust` - Multi-agent trust verification
15. `audit_tool_permissions` - Privilege escalation detection
16. `classify_agent_autonomy` - Agent autonomy classification
17. `assess_dpdp_compliance` - India DPDP Act compliance

### Security

- Ed25519 cryptographic signing for audit certificates
- Zero-trust architecture with OAuth 2.1
- On-premise deployment with no external dependencies
- Merkle audit trail for tamper-evident evidence

## [1.0.0] - 2026-06-15

### Added

- Initial release with core audit pipeline
- Basic EU AI Act compliance checking
- Docker deployment support
