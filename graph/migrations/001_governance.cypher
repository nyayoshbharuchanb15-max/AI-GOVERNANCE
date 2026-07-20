// Governance control graph — constraints (idempotent). ARCHITECTURE.md §4.1.
CREATE CONSTRAINT gov_model_id IF NOT EXISTS FOR (m:Model) REQUIRE m.modelId IS UNIQUE;
CREATE CONSTRAINT gov_dataset_id IF NOT EXISTS FOR (d:Dataset) REQUIRE d.datasetId IS UNIQUE;
CREATE CONSTRAINT gov_activity_id IF NOT EXISTS FOR (a:ProcessingActivity) REQUIRE a.activityId IS UNIQUE;
CREATE CONSTRAINT gov_article_id IF NOT EXISTS FOR (r:RegulatoryArticle) REQUIRE r.articleId IS UNIQUE;
CREATE CONSTRAINT gov_control_id IF NOT EXISTS FOR (c:Control) REQUIRE c.controlId IS UNIQUE;
CREATE CONSTRAINT gov_execution_id IF NOT EXISTS FOR (t:TestExecution) REQUIRE t.executionId IS UNIQUE;
CREATE CONSTRAINT gov_evidence_id IF NOT EXISTS FOR (e:EvidenceArtifact) REQUIRE e.evidenceId IS UNIQUE;
CREATE CONSTRAINT gov_run_id IF NOT EXISTS FOR (r:AuditRun) REQUIRE r.runId IS UNIQUE;
CREATE CONSTRAINT gov_phase_result_id IF NOT EXISTS FOR (p:PhaseResult) REQUIRE p.resultId IS UNIQUE;
CREATE CONSTRAINT gov_remediation_id IF NOT EXISTS FOR (t:RemediationTask) REQUIRE t.taskId IS UNIQUE;
CREATE CONSTRAINT gov_certificate_id IF NOT EXISTS FOR (c:Certificate) REQUIRE c.certificateId IS UNIQUE;
