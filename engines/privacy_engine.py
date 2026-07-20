# SPDX-License-Identifier: Apache-2.0
"""Phase 4 — Data Protection & Privacy Checks (GDPR + DPDP Act)."""
from __future__ import annotations

ART9_BASES = {"explicit_consent", "employment_law", "vital_interests",
              "substantial_public_interest", "health"}
TRANSFER_MECHANISMS = {"adequacy_decision", "scc", "bcr"}


def assess(context: dict, dp: dict) -> dict:
    regions = (context.get("deploymentContext") or {}).get("regions", [])
    risk_tier = context.get("riskTier", "minimal")
    special_categories = _special_categories(context)
    findings: list[dict] = []
    blockers: list[dict] = []
    articles: list[dict] = []

    def finding(check: str, framework: str, article: str, status: str, detail: str):
        findings.append({"check": check, "framework": framework, "article": article,
                         "status": status, "detail": detail})
        articles.append({"framework": framework, "article": article, "title": check})

    processes_personal = dp.get("processesPersonalData", False)

    if processes_personal:
        basis = dp.get("lawfulBasis", "none")
        if basis == "none":
            finding("Lawful basis of processing", "GDPR", "Art. 6", "fail",
                    "Personal data is processed without a lawful basis.")
            blockers.append({"code": "NO_LAWFUL_BASIS", "framework": "GDPR", "article": "Art. 6",
                             "reason": "No lawful basis declared for personal data processing.",
                             "remediation": "Establish and document an Art. 6(1) lawful basis."})
        else:
            finding("Lawful basis of processing", "GDPR", "Art. 6", "pass",
                    f"Lawful basis: {basis}.")

        if special_categories:
            sc_basis = dp.get("specialCategoryBasis", "none")
            if sc_basis not in ART9_BASES:
                finding("Special category data", "GDPR", "Art. 9", "fail",
                        f"Special categories {sorted(special_categories)} processed without an Art. 9(2) condition.")
                blockers.append({"code": "SPECIAL_CATEGORY_NO_BASIS", "framework": "GDPR",
                                 "article": "Art. 9",
                                 "reason": "Special category data processed without an Art. 9(2) condition.",
                                 "remediation": "Obtain explicit consent or another Art. 9(2) condition, or stop processing."})
            else:
                finding("Special category data", "GDPR", "Art. 9", "pass",
                        f"Art. 9(2) condition: {sc_basis}.")

        for transfer in dp.get("crossBorderTransfers", []):
            mech = transfer.get("mechanism", "none")
            dest = transfer.get("destination", "unknown")
            if mech not in TRANSFER_MECHANISMS:
                finding("Cross-border transfer", "GDPR", "Art. 44-49", "fail",
                        f"Transfer to {dest} lacks a valid transfer mechanism.")
                blockers.append({"code": "UNLAWFUL_TRANSFER", "framework": "GDPR",
                                 "article": "Art. 44-49",
                                 "reason": f"Cross-border transfer to {dest} without adequacy/SCC/BCR.",
                                 "remediation": "Adopt SCCs/BCRs or restrict the transfer to adequate jurisdictions."})
            else:
                finding("Cross-border transfer", "GDPR", "Art. 44-49", "pass",
                        f"Transfer to {dest} covered by {mech}.")

        if risk_tier == "high":
            if not dp.get("dpiaConducted"):
                finding("Data Protection Impact Assessment", "GDPR", "Art. 35", "fail",
                        "High-risk AI system without a DPIA.")
                blockers.append({"code": "DPIA_MISSING_HIGH_RISK", "framework": "GDPR",
                                 "article": "Art. 35",
                                 "reason": "DPIA not conducted for a high-risk system.",
                                 "remediation": "Conduct and document a DPIA before deployment."})
            else:
                finding("Data Protection Impact Assessment", "GDPR", "Art. 35", "pass",
                        "DPIA conducted.")

        finding("Privacy by design and by default", "GDPR", "Art. 25",
                "pass" if dp.get("privacyByDesign") else "warning",
                "Privacy-by-design measures declared." if dp.get("privacyByDesign")
                else "Privacy-by-design measures not declared.")
        finding("Data minimisation", "GDPR", "Art. 5",
                "pass" if dp.get("dataMinimisationApplied") else "warning",
                "Data minimisation applied." if dp.get("dataMinimisationApplied")
                else "Data minimisation not declared (Art. 5(1)(c)).")
        retention = dp.get("retentionPeriodDays")
        finding("Storage limitation / retention", "GDPR", "Art. 5",
                "pass" if retention else "warning",
                f"Retention period: {retention} days." if retention
                else "No retention period declared (Art. 5(1)(e)).")
        finding("Records of processing activities", "GDPR", "Art. 30", "pass",
                f"{len(context.get('processingActivities', []))} processing activities registered at intake.")

        if "IN" in regions:
            if not dp.get("consentMechanism"):
                finding("DPDP consent", "DPDP-ACT", "Sec. 6", "fail",
                        "No consent mechanism for Indian data principals.")
                blockers.append({"code": "DPDP_NO_CONSENT", "framework": "DPDP-ACT",
                                 "article": "Sec. 6",
                                 "reason": "Personal data of Indian data principals without a consent mechanism.",
                                 "remediation": "Implement free, specific, informed, unambiguous consent (Sec. 6)."})
            else:
                finding("DPDP consent", "DPDP-ACT", "Sec. 6", "pass",
                        "Consent mechanism in place.")
            finding("Data fiduciary obligations", "DPDP-ACT", "Sec. 8",
                    "pass" if dp.get("privacyByDesign") else "warning",
                    "Security safeguards declared." if dp.get("privacyByDesign")
                    else "Security safeguards not declared (Sec. 8(5)).")
            finding("DPO appointment (Significant Data Fiduciary)", "DPDP-ACT", "Sec. 10",
                    "pass" if dp.get("dpoAppointed") else "warning",
                    "DPO appointed." if dp.get("dpoAppointed")
                    else "No DPO — required only if designated a Significant Data Fiduciary (Sec. 10(2)(a)).")
    else:
        finding("Personal data processing", "GDPR", "Art. 5", "pass",
                "No personal data processed — GDPR/DPDP checks not triggered.")

    summary = {"passed": sum(1 for f in findings if f["status"] == "pass"),
               "warnings": sum(1 for f in findings if f["status"] == "warning"),
               "failed": sum(1 for f in findings if f["status"] == "fail")}
    return {"findings": findings, "summary": summary,
            "_articles": _dedupe(articles), "_blockers": blockers}


def _special_categories(context: dict) -> set:
    cats: set = set()
    for act in context.get("processingActivities", []):
        cats.update(act.get("specialCategories", []))
    for ds in context.get("datasets", []):
        cats.update(ds.get("specialCategories", []))
    return cats


def _dedupe(articles: list[dict]) -> list[dict]:
    seen = {}
    for a in articles:
        seen[(a["framework"], a["article"])] = a
    return list(seen.values())
