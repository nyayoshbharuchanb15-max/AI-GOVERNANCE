# SPDX-License-Identifier: Apache-2.0
"""Phase 2 — Regulatory Scope Mapping (article-level applicability from intake context)."""
from __future__ import annotations


def build_scope_map(context: dict) -> dict:
    regions = (context.get("deploymentContext") or {}).get("regions", [])
    autonomy = (context.get("deploymentContext") or {}).get("autonomyLevel", "assistive")
    activities = context.get("processingActivities", [])
    datasets = context.get("datasets", [])
    personal_data = any(ds.get("containsPersonalData") for ds in datasets) or bool(activities)
    special = any(a.get("specialCategories") for a in activities) or \
        any(d.get("specialCategories") for d in datasets)
    cross_border = any(a.get("crossBorder") for a in activities)

    scope_map: list[dict] = []

    def add(framework: str, article: str, title: str, trigger: str):
        scope_map.append({"framework": framework, "article": article,
                          "title": title, "trigger": trigger})

    if "EU" in regions:
        eu = "placed on the EU market / used in the EU"
        add("EU-AI-ACT", "Art. 5", "Prohibited AI practices", f"Screening mandatory — {eu}")
        add("EU-AI-ACT", "Art. 6", "Classification rules for high-risk AI systems", eu)
        add("EU-AI-ACT", "Art. 10", "Data and data governance", eu)
        add("EU-AI-ACT", "Art. 11", "Technical documentation", eu)
        add("EU-AI-ACT", "Art. 12", "Record-keeping", eu)
        add("EU-AI-ACT", "Art. 13", "Transparency and provision of information", eu)
        add("EU-AI-ACT", "Art. 14", "Human oversight", eu)
        add("EU-AI-ACT", "Art. 15", "Accuracy, robustness and cybersecurity", eu)
        add("EU-AI-ACT", "Art. 72", "Post-market monitoring", eu)

    if personal_data and "EU" in regions:
        pd = "personal data of EU data subjects processed"
        add("GDPR", "Art. 5", "Principles relating to processing", pd)
        add("GDPR", "Art. 6", "Lawfulness of processing", pd)
        add("GDPR", "Art. 25", "Data protection by design and by default", pd)
        add("GDPR", "Art. 30", "Records of processing activities", pd)
        add("GDPR", "Art. 32", "Security of processing", pd)
        add("GDPR", "Art. 35", "Data protection impact assessment", pd)
        if special:
            add("GDPR", "Art. 9", "Special categories of personal data",
                "special category data declared in intake")
        if autonomy in ("supervised", "autonomous"):
            add("GDPR", "Art. 22", "Automated individual decision-making",
                f"autonomy level '{autonomy}' implies automated decisions")
        if cross_border:
            add("GDPR", "Art. 44-49", "Transfers to third countries",
                "cross-border processing activity declared")

    if personal_data and "IN" in regions:
        dpdp = "digital personal data of Indian data principals processed"
        add("DPDP-ACT", "Sec. 5", "Notice", dpdp)
        add("DPDP-ACT", "Sec. 6", "Consent", dpdp)
        add("DPDP-ACT", "Sec. 8", "General obligations of Data Fiduciary", dpdp)
        add("DPDP-ACT", "Sec. 10", "Significant Data Fiduciary obligations", dpdp)
        add("DPDP-ACT", "Sec. 11", "Right to access information", dpdp)
        add("DPDP-ACT", "Sec. 12", "Right to correction and erasure", dpdp)
        add("DPDP-ACT", "Sec. 13", "Right of grievance redressal", dpdp)
        if cross_border:
            add("DPDP-ACT", "Sec. 16", "Cross-border transfer",
                "cross-border processing activity declared")

    baseline = "voluntary organizational baseline (always in scope)"
    add("NIST-AI-RMF", "GOVERN 1.2", "Trustworthy AI characteristics integrated into policy", baseline)
    add("NIST-AI-RMF", "MAP 1.1", "Context and risk identification", baseline)
    add("NIST-AI-RMF", "MEASURE 2.2", "Evaluations of trustworthiness", baseline)
    add("ISO-42001", "Clause 6.1", "Actions to address risks and opportunities", baseline)
    add("ISO-42001", "Clause 7.5", "Documented information", baseline)
    add("ISO-42001", "Clause 8.2", "AI risk assessment", baseline)
    add("ISO-42001", "Clause 9.1", "Monitoring, measurement, analysis and evaluation", baseline)

    frameworks = sorted({e["framework"] for e in scope_map})
    return {"frameworks": frameworks, "scopeMap": scope_map}
