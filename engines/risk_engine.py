# SPDX-License-Identifier: Apache-2.0
"""Phase 3 — Risk Classification (EU AI Act Art. 5, 6 + Annex III, 50)."""
from __future__ import annotations

ANNEX_III = {"biometric_identification", "critical_infrastructure", "education",
             "employment", "essential_services", "law_enforcement",
             "migration_border", "justice_democracy"}


def classify(risk_inputs: dict) -> dict:
    rationale: list[str] = []
    articles: list[dict] = []
    blockers: list[dict] = []

    prohibited = []
    if risk_inputs.get("usesSocialScoring"):
        prohibited.append("social scoring of natural persons (Art. 5(1)(c))")
    if risk_inputs.get("usesRealtimeBiometricId"):
        prohibited.append("real-time remote biometric identification in public spaces (Art. 5(1)(h))")
    if risk_inputs.get("usesManipulativeTechniques"):
        prohibited.append("manipulative/deceptive techniques causing harm (Art. 5(1)(a))")

    if prohibited:
        tier = "prohibited"
        rationale.extend(prohibited)
        articles.append({"framework": "EU-AI-ACT", "article": "Art. 5",
                         "title": "Prohibited AI practices"})
        for reason in prohibited:
            blockers.append({
                "code": "PROHIBITED_PRACTICE", "framework": "EU-AI-ACT", "article": "Art. 5",
                "reason": f"Prohibited practice detected: {reason}",
                "remediation": "Remove the prohibited capability; Art. 5 practices cannot be certified."})
    else:
        annex_cats = sorted(set(risk_inputs.get("annexIIICategories", [])) & ANNEX_III)
        if annex_cats or risk_inputs.get("isSafetyComponent"):
            tier = "high"
            if annex_cats:
                rationale.append(f"Annex III high-risk use case(s): {', '.join(annex_cats)}")
            if risk_inputs.get("isSafetyComponent"):
                rationale.append("Safety component of a regulated product (Art. 6(1))")
            articles.append({"framework": "EU-AI-ACT", "article": "Art. 6",
                             "title": "Classification rules for high-risk AI systems"})
            articles.append({"framework": "EU-AI-ACT", "article": "Annex III",
                             "title": "High-risk AI systems"})
        elif risk_inputs.get("interactsWithHumans") or risk_inputs.get("generatesSyntheticContent"):
            tier = "limited"
            rationale.append("Transparency obligations apply (interaction with humans / synthetic content)")
            articles.append({"framework": "EU-AI-ACT", "article": "Art. 50",
                             "title": "Transparency obligations"})
        else:
            tier = "minimal"
            rationale.append("No prohibited, Annex III, or transparency-triggering characteristics declared")

    articles.append({"framework": "NIST-AI-RMF", "article": "MAP 1.1",
                     "title": "Context and risk identification"})
    return {"riskTier": tier, "rationale": rationale,
            "applicableArticles": [f"{a['framework']}:{a['article']}" for a in articles],
            "_articles": articles, "_blockers": blockers}
