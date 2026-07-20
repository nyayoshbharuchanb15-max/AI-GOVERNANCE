# SPDX-License-Identifier: Apache-2.0
"""Lineage writers/readers for the control graph (ARCHITECTURE.md §4.1)."""
from __future__ import annotations
import uuid
from typing import Any, Optional

from graph.client import graph


async def record_intake(run_id: str, model_id: str, model_version: str,
                        activities: list[dict], datasets: list[dict],
                        reaudit_of: Optional[str] = None) -> None:
    await graph.run(
        """MERGE (m:Model {modelId: $model_id})
           SET m.version = $model_version
           MERGE (r:AuditRun {runId: $run_id})
           SET r.status = 'in_progress'
           MERGE (r)-[:AUDITS]->(m)""",
        {"model_id": model_id, "model_version": model_version, "run_id": run_id})
    if reaudit_of:
        await graph.run(
            """MATCH (r:AuditRun {runId: $run_id}), (prev:AuditRun {runId: $prev})
               MERGE (r)-[:REAUDIT_OF]->(prev)""",
            {"run_id": run_id, "prev": reaudit_of})
    for act in activities:
        await graph.run(
            """MATCH (m:Model {modelId: $model_id})
               MERGE (a:ProcessingActivity {activityId: $activity_id})
               SET a.name = $name, a.purpose = $purpose, a.crossBorder = $cross_border
               MERGE (m)-[:PERFORMS]->(a)""",
            {"model_id": model_id, "activity_id": act["activityId"], "name": act["name"],
             "purpose": act["purpose"], "cross_border": act.get("crossBorder", False)})
    for ds in datasets:
        await graph.run(
            """MATCH (m:Model {modelId: $model_id})
               MERGE (d:Dataset {datasetId: $dataset_id})
               SET d.version = $version, d.containsPersonalData = $personal
               MERGE (m)-[:TRAINED_ON]->(d)""",
            {"model_id": model_id, "dataset_id": ds["datasetId"],
             "version": ds.get("version", "1"), "personal": ds.get("containsPersonalData", False)})


async def record_scope_mapping(run_id: str, model_id: str, scope_map: list[dict]) -> None:
    for entry in scope_map:
        article_id = f"{entry['framework']}:{entry['article']}"
        await graph.run(
            """MERGE (ra:RegulatoryArticle {articleId: $article_id})
               SET ra.framework = $framework, ra.article = $article, ra.title = $title""",
            {"article_id": article_id, "framework": entry["framework"],
             "article": entry["article"], "title": entry.get("title", "")})
        await graph.run(
            """MATCH (m:Model {modelId: $model_id})-[:PERFORMS]->(a:ProcessingActivity),
                     (ra:RegulatoryArticle {articleId: $article_id})
               MERGE (a)-[:GOVERNED_BY]->(ra)""",
            {"model_id": model_id, "article_id": article_id})


async def record_phase(run_id: str, phase_key: str, phase_number: int, status: str,
                       result_id: str, evidence_id: str, integrity_hash: str,
                       control_version: str, articles: list[dict],
                       blockers: list[dict]) -> None:
    control_id = f"CTRL-{phase_key}"
    execution_id = str(uuid.uuid4())
    await graph.run(
        """MATCH (r:AuditRun {runId: $run_id})
           MERGE (c:Control {controlId: $control_id})
           SET c.version = $control_version, c.phase = $phase_key
           CREATE (p:PhaseResult {resultId: $result_id, phase: $phase_key,
                                  phaseNumber: $phase_number, status: $status})
           CREATE (t:TestExecution {executionId: $execution_id, phase: $phase_key,
                                    runId: $run_id, status: $status})
           CREATE (e:EvidenceArtifact {evidenceId: $evidence_id,
                                       integrityHash: $integrity_hash, phase: $phase_key})
           MERGE (r)-[:INCLUDES]->(p)
           MERGE (p)-[:EXECUTED]->(t)
           MERGE (c)-[:VERIFIED_BY]->(t)
           MERGE (t)-[:PRODUCED]->(e)""",
        {"run_id": run_id, "control_id": control_id, "control_version": control_version,
         "phase_key": phase_key, "phase_number": phase_number, "status": status,
         "result_id": result_id, "execution_id": execution_id,
         "evidence_id": evidence_id, "integrity_hash": integrity_hash})
    for art in articles:
        article_id = f"{art['framework']}:{art['article']}"
        await graph.run(
            """MERGE (ra:RegulatoryArticle {articleId: $article_id})
               SET ra.framework = $framework, ra.article = $article
               WITH ra MATCH (c:Control {controlId: $control_id})
               MERGE (c)-[:SATISFIES]->(ra)""",
            {"article_id": article_id, "framework": art["framework"],
             "article": art["article"], "control_id": control_id})
    for blocker in blockers:
        await graph.run(
            """MATCH (p:PhaseResult {resultId: $result_id})
               CREATE (task:RemediationTask {taskId: $task_id, code: $code,
                                             description: $remediation, severity: 'blocker',
                                             article: $article})
               MERGE (p)-[:RAISED]->(task)""",
            {"result_id": result_id, "task_id": str(uuid.uuid4()),
             "code": blocker.get("code", ""), "remediation": blocker.get("remediation", ""),
             "article": f"{blocker.get('framework','')}:{blocker.get('article','')}"})


async def record_certificate(run_id: str, certificate_id: str, status: str = "active") -> None:
    await graph.run(
        """MATCH (r:AuditRun {runId: $run_id})
           MERGE (c:Certificate {certificateId: $certificate_id})
           SET c.status = $status
           MERGE (r)-[:CERTIFIED_BY]->(c)""",
        {"run_id": run_id, "certificate_id": certificate_id, "status": status})


async def set_certificate_status(certificate_id: str, status: str) -> None:
    await graph.run(
        "MATCH (c:Certificate {certificateId: $cid}) SET c.status = $status",
        {"cid": certificate_id, "status": status})


async def set_run_status(run_id: str, status: str) -> None:
    await graph.run(
        "MATCH (r:AuditRun {runId: $run_id}) SET r.status = $status",
        {"run_id": run_id, "status": status})


async def get_run_lineage(run_id: str) -> dict[str, Any]:
    nodes = await graph.run(
        """MATCH (r:AuditRun {runId: $run_id})
           OPTIONAL MATCH p = (r)-[*1..4]-(n)
           WITH collect(DISTINCT n) AS ns, r
           UNWIND (ns + r) AS node
           RETURN DISTINCT labels(node) AS labels, properties(node) AS props""",
        {"run_id": run_id})
    edges = await graph.run(
        """MATCH (r:AuditRun {runId: $run_id})
           OPTIONAL MATCH p = (r)-[*1..4]-()
           UNWIND relationships(p) AS rel
           RETURN DISTINCT type(rel) AS type""",
        {"run_id": run_id})
    return {"nodes": nodes, "relationshipTypes": sorted({e["type"] for e in edges if e.get("type")})}


async def resolve_impact_nodes(model_id: str, trigger_type: str,
                               dataset_id: Optional[str] = None) -> list[dict]:
    """Impact Scope Resolver — affected graph nodes for a reaudit trigger."""
    if trigger_type == "dataset_revision" and dataset_id:
        return await graph.run(
            """MATCH (d:Dataset {datasetId: $dataset_id})<-[:TRAINED_ON]-(m:Model)
               OPTIONAL MATCH (m)<-[:AUDITS]-(r:AuditRun)-[:INCLUDES]->(p:PhaseResult)
               RETURN DISTINCT labels(d)[0] AS label, d.datasetId AS id
               UNION
               MATCH (d:Dataset {datasetId: $dataset_id})<-[:TRAINED_ON]-(m:Model)
               RETURN DISTINCT labels(m)[0] AS label, m.modelId AS id""",
            {"dataset_id": dataset_id})
    return await graph.run(
        """MATCH (m:Model {modelId: $model_id})
           OPTIONAL MATCH (m)<-[:AUDITS]-(r:AuditRun)-[:INCLUDES]->(p:PhaseResult)
                          -[:EXECUTED]->(t:TestExecution)<-[:VERIFIED_BY]-(c:Control)
           WITH collect(DISTINCT {label: 'Control', id: c.controlId}) AS controls, m
           RETURN 'Model' AS label, m.modelId AS id
           UNION
           MATCH (m:Model {modelId: $model_id})<-[:AUDITS]-(r:AuditRun)
                 -[:INCLUDES]->(p:PhaseResult)-[:EXECUTED]->(t:TestExecution)
                 <-[:VERIFIED_BY]-(c:Control)
           RETURN DISTINCT 'Control' AS label, c.controlId AS id""",
        {"model_id": model_id})
