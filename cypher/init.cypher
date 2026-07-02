// ═══════════════════════════════════════════════════════════════════
//  AI Governance — Neo4j Provenance Graph Schema
//  ISO/IEC 42001:2023 Clause 7.4.3 — Supply Chain Traceability
//  ═══════════════════════════════════════════════════════════════════
//
//  This Cypher script initializes the Neo4j graph schema for AI
//  model supply chain provenance tracking. It creates:
//
//    1. Constraints & indexes for query performance
//    2. Node labels: Model, Dataset, Transform, Deployment, Component
//    3. Relationship types: TRAINED_ON, FINE_TUNED_ON, DEPLOYED_ON,
//       CONTAINS, DERIVED_FROM
//
//  Regulatory mappings:
//    • EU AI Act Art. 10 — Data Governance and traceability
//    • EU AI Act Art. 12 — Technical Documentation
//    • NIST AI RMF GOVERN 1.2 — Supply Chain Transparency
//    • ISO/IEC 42001:2023 Clause 7.4.3 — Supply Chain Traceability

// ─── Constraints ─────────────────────────────────────────────────
//  Ensure uniqueness of node identities

CREATE CONSTRAINT model_id_unique IF NOT EXISTS
FOR (m:Model) REQUIRE m.modelId IS UNIQUE;

CREATE CONSTRAINT dataset_id_unique IF NOT EXISTS
FOR (d:Dataset) REQUIRE d.datasetId IS UNIQUE;

CREATE CONSTRAINT transform_id_unique IF NOT EXISTS
FOR (t:Transform) REQUIRE t.transformId IS UNIQUE;

CREATE CONSTRAINT deployment_id_unique IF NOT EXISTS
FOR (d:Deployment) REQUIRE d.deploymentId IS UNIQUE;

CREATE CONSTRAINT component_id_unique IF NOT EXISTS
FOR (c:Component) REQUIRE c.componentId IS UNIQUE;

// ─── Indexes ─────────────────────────────────────────────────────
//  Accelerate property lookups for common queries

CREATE INDEX model_name_index IF NOT EXISTS
FOR (m:Model) ON (m.name);

CREATE INDEX dataset_license_index IF NOT EXISTS
FOR (d:Dataset) ON (d.license);

CREATE INDEX component_license_index IF NOT EXISTS
FOR (c:Component) ON (c.license);

CREATE INDEX ip_clearance_index IF NOT EXISTS
FOR (c:Component) ON (c.ipCleared);

// ─── Seed Node: Schema Initialization Marker ─────────────────────

MERGE (schema:Model {modelId: '__schema_init__'})
SET schema.name = 'Provenance Graph Schema',
    schema.version = '1.0.0',
    schema.description = 'AI Governance supply chain provenance graph',
    schema.initTimestamp = timestamp(),
    schema.supportedRegulations = [
        'EU AI Act (Regulation 2024/1689)',
        'NIST AI RMF (NIST AI 100-1)',
        'ISO/IEC 42001:2023',
        'GDPR (Regulation 2016/679)'
    ];

// ─── Query Templates (for documentation / application use) ───────
//  These are not executed but illustrate the graph query patterns
//  used by the supply chain audit service.

// -- Example 1: Full provenance trace for a model
// MATCH (m:Model {modelId: 'model-llm-v2'})
// OPTIONAL MATCH path = (m)-[*1..3]-(connected)
// RETURN nodes(path) AS lineage, relationships(path) AS dependencies

// -- Example 2: IP clearance audit
// MATCH (m:Model {modelId: 'model-llm-v2'})
// OPTIONAL MATCH (m)-[*1..3]-(component:Component)
// WHERE component.ipCleared = false
// RETURN component.name AS unclearedComponent,
//        component.license AS license,
//        component.origin AS origin

// -- Example 3: License compatibility check
// MATCH (m:Model {modelId: 'model-llm-v2'})
// OPTIONAL MATCH (m)-[*1..3]-(component:Component)
// RETURN component.name, component.license,
//        component.ipCleared,
//        CASE
//          WHEN component.license IN ['MIT', 'Apache-2.0', 'BSD-3'] THEN 'COMPATIBLE'
//          ELSE 'REVIEW_REQUIRED'
//        END AS licenseStatus
