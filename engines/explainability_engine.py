# SPDX-License-Identifier: Apache-2.0
"""Phase 7 — Explainability & Human Oversight (EU AI Act Art. 12, 13, 14, 86; GDPR Art. 22)."""
from __future__ import annotations

EXPLAINABILITY_METHODS = {"shap", "lime", "integrated_gradients", "attention_maps", "rule_based"}


def verify(risk_tier: str, oversight: dict, explainability: dict) -> dict:
    findings: list[dict] = []
    blockers: list[dict] = []
    score = 100
    high_risk = risk_tier == "high"

    def finding(check: str, framework: str, article: str, status: str, detail: str):
        findings.append({"check": check, "framework": framework, "article": article,
                         "status": status, "detail": detail})

    if oversight.get("hasKillSwitch"):
        finding("Kill switch / stop capability", "EU-AI-ACT", "Art. 14", "pass",
                "Intervention/stop capability present (Art. 14(4)(e)).")
    else:
        score -= 30
        status = "fail" if high_risk else "warning"
        finding("Kill switch / stop capability", "EU-AI-ACT", "Art. 14", status,
                "No stop capability declared.")
        if high_risk:
            blockers.append({
                "code": "NO_KILL_SWITCH", "framework": "EU-AI-ACT", "article": "Art. 14",
                "reason": "Art. 14(4)(e) requires the ability to intervene or halt the system "
                          "for ALL high-risk AI systems.",
                "remediation": "Implement and document a kill-switch/stop control."})

    has_oversight = oversight.get("hasHumanInTheLoop") or oversight.get("overrideProcedureDocumented")
    if has_oversight:
        finding("Human oversight measures", "EU-AI-ACT", "Art. 14", "pass",
                "Human-in-the-loop and/or documented override procedure in place.")
    else:
        score -= 30
        status = "fail" if high_risk else "warning"
        finding("Human oversight measures", "EU-AI-ACT", "Art. 14", status,
                "No human-in-the-loop and no documented override procedure.")
        if high_risk:
            blockers.append({
                "code": "NO_HUMAN_OVERSIGHT", "framework": "EU-AI-ACT", "article": "Art. 14",
                "reason": "High-risk system without effective human oversight measures.",
                "remediation": "Assign oversight roles and document an override procedure."})

    method = explainability.get("method", "none")
    if method in EXPLAINABILITY_METHODS:
        finding("Explainability method", "EU-AI-ACT", "Art. 13", "pass",
                f"Explainability method: {method}.")
    else:
        score -= 25
        status = "fail" if high_risk else "warning"
        finding("Explainability method", "EU-AI-ACT", "Art. 13", status,
                "No explainability method configured.")
        if high_risk:
            blockers.append({
                "code": "NO_EXPLAINABILITY", "framework": "EU-AI-ACT", "article": "Art. 13",
                "reason": "High-risk system outputs cannot be interpreted by deployers "
                          "(Art. 13) nor explained to affected persons (Art. 86).",
                "remediation": "Integrate an explainability method (e.g. SHAP/LIME/rule-based)."})

    if explainability.get("decisionLogsRetained"):
        finding("Automatic event logging", "EU-AI-ACT", "Art. 12", "pass",
                f"Decision logs retained ({explainability.get('logRetentionDays', 'n/a')} days).")
    else:
        score -= 15
        status = "fail" if high_risk else "warning"
        finding("Automatic event logging", "EU-AI-ACT", "Art. 12", status,
                "Decision logs are not retained.")
        if high_risk:
            blockers.append({
                "code": "NO_DECISION_LOGS", "framework": "EU-AI-ACT", "article": "Art. 12",
                "reason": "Record-keeping (automatic logging) is mandatory for high-risk systems.",
                "remediation": "Enable automatic decision/event logging with retention."})

    finding("Meaningful information about automated decisions", "GDPR", "Art. 22",
            "pass" if explainability.get("userFacingExplanations") else "warning",
            "User-facing explanations provided." if explainability.get("userFacingExplanations")
            else "No user-facing explanations for automated decisions.")

    articles = [
        {"framework": "EU-AI-ACT", "article": "Art. 12", "title": "Record-keeping"},
        {"framework": "EU-AI-ACT", "article": "Art. 13", "title": "Transparency and provision of information to deployers"},
        {"framework": "EU-AI-ACT", "article": "Art. 14", "title": "Human oversight"},
        {"framework": "EU-AI-ACT", "article": "Art. 86", "title": "Right to explanation of individual decision-making"},
        {"framework": "GDPR", "article": "Art. 22", "title": "Automated individual decision-making"},
    ]
    return {"oversightScore": max(score, 0), "findings": findings,
            "_articles": articles, "_blockers": blockers}
