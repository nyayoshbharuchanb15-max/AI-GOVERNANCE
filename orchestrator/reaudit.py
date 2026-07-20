# SPDX-License-Identifier: Apache-2.0
"""Reaudit pattern: Impact Scope Resolver → selective re-run → diff → cert action."""
from __future__ import annotations
import logging
from typing import Optional

from events.fabric import fabric
from graph import lineage
from orchestrator.pipeline import execute_phase
from orchestrator.state_machine import PHASE_NUMBERS, PHASE_ORDER, PipelineError
from store import evidence as store

logger = logging.getLogger("orchestrator.reaudit")

# AUDIT_PIPELINE.md §11 — impact matrix
IMPACT_MATRIX: dict[str, list[str]] = {
    "model_version_change": ["risk", "fairness", "robustness", "explainability"],
    "dataset_revision": ["data_protection", "fairness"],
    "policy_update": ["scope", "risk", "data_protection"],
    "critical_incident": ["robustness", "explainability"],
    "drift_threshold_breach": ["fairness", "robustness"],
}
DEPENDENT_PHASES = ["certification", "monitoring"]


def _diff_entry(prev: dict, new: dict) -> dict:
    prev_blockers = {b["code"] for b in prev.get("blocker_reasons", [])}
    new_blockers = {b["code"] for b in new.get("blockers", [])}
    return {
        "phase": prev["phase_key"],
        "previousStatus": prev["status"],
        "newStatus": new["status"],
        "previousHash": prev["integrity_hash"],
        "newHash": new["integrityHash"],
        "changed": prev["integrity_hash"] != new["integrityHash"],
        "blockersAdded": sorted(new_blockers - prev_blockers),
        "blockersResolved": sorted(prev_blockers - new_blockers),
    }


async def execute_reaudit(model_id: str, trigger: dict, actor: str) -> dict:
    trigger_type = trigger["type"]
    if trigger_type not in IMPACT_MATRIX:
        raise PipelineError("UNKNOWN_TRIGGER", f"Unknown trigger type '{trigger_type}'",
                            status_code=400)
    prev_run = await store.latest_certified_run(model_id)
    if not prev_run:
        raise PipelineError("NO_CERTIFIED_RUN",
                            f"No certified run found for model '{model_id}'", status_code=404)
    prev_results = {r["phase_key"]: r for r in await store.get_phase_results(prev_run["run_id"])}

    impacted = [p for p in PHASE_ORDER if p in IMPACT_MATRIX[trigger_type]]
    carried = [p for p in PHASE_ORDER[:7] if p not in impacted and p in prev_results]
    affected_nodes = await lineage.resolve_impact_nodes(
        model_id, trigger_type, dataset_id=trigger.get("datasetId"))

    # New run with (possibly updated) context
    context = dict(prev_run["context"])
    new_version = trigger.get("newModelVersion") or prev_run["model_version"]
    context["modelVersion"] = new_version
    new_run_id = await store.create_run(model_id, new_version, context,
                                        reaudit_of=prev_run["run_id"], trigger=trigger)
    await lineage.record_intake(new_run_id, model_id, new_version,
                                context.get("processingActivities", []),
                                context.get("datasets", []),
                                reaudit_of=prev_run["run_id"])

    # Carry forward unaffected phases (original hashes retained)
    for phase in carried:
        pr = prev_results[phase]
        await store.insert_phase_result(
            new_run_id, phase, PHASE_NUMBERS[phase], pr["status"], pr["inputs"],
            pr["outputs"], pr["legal_mappings"], pr["blocker_reasons"],
            pr["control_version"], pr["integrity_hash"], pr["prev_hash"],
            actor=actor, carried_forward=True, origin_run_id=prev_run["run_id"])

    # Selective re-run of impacted phases using stored immutable inputs
    # (plus trigger deltas supplied via updatedPhaseInputs, e.g. a revised dataset sample)
    updated_inputs = trigger.get("updatedPhaseInputs") or {}
    findings_diff: list[dict] = []
    blocked = False
    for phase in impacted:
        prev_inputs = updated_inputs.get(phase) or prev_results.get(phase, {}).get("inputs", {})
        result = await execute_phase(new_run_id, phase, prev_inputs, actor)
        if phase in prev_results:
            findings_diff.append(_diff_entry(prev_results[phase], result))
        if result["status"] == "blocked":
            blocked = True
            break

    prev_cert = await store.get_certificate_for_run(prev_run["run_id"])
    certificate_action: dict = {"previousCertificateId": prev_cert["certificate_id"] if prev_cert else None}

    if blocked:
        if prev_cert and prev_cert["status"] == "active":
            reason = f"Reaudit trigger '{trigger_type}' produced blocker finding(s)"
            await store.revoke_certificate(prev_cert["certificate_id"], reason)
            await lineage.set_certificate_status(prev_cert["certificate_id"], "revoked")
            certificate_action.update({"action": "revoked", "reason": reason})
        else:
            certificate_action.update({"action": "blocked_no_reissue"})
    else:
        cert_inputs = dict(prev_results.get("certification", {}).get("inputs",
                           {"issuer": {"name": "AI Governance Authority"}, "validityDays": 365}))
        cert_result = await execute_phase(
            new_run_id, "certification", cert_inputs, actor,
            supersedes=prev_cert["certificate_id"] if prev_cert else None)
        mon_inputs = dict(prev_results.get("monitoring", {}).get("inputs", {"monitors": {}}))
        await execute_phase(new_run_id, "monitoring", mon_inputs, actor)
        await store.update_run_status(prev_run["run_id"], "superseded")
        await lineage.set_run_status(prev_run["run_id"], "superseded")
        certificate_action.update({"action": "reissued",
                                   "newCertificateId": cert_result["outputs"]["certificateId"]})

    new_run = await store.get_run(new_run_id)
    result = {
        "reauditRunId": new_run_id,
        "previousRunId": prev_run["run_id"],
        "runStatus": new_run["status"],
        "impactScope": {
            "trigger": trigger,
            "impactedPhases": impacted,
            "dependentPhases": DEPENDENT_PHASES,
            "carriedForwardPhases": carried,
            "affectedGraphNodes": affected_nodes,
        },
        "findingsDiff": findings_diff,
        "certificateAction": certificate_action,
    }
    await fabric.publish(
        "governance:phase-events", "reaudit.completed",
        {"runId": new_run_id, "modelId": model_id, "triggerType": trigger_type,
         "certificateAction": certificate_action.get("action")})
    return result
