# SPDX-License-Identifier: Apache-2.0
"""Phase 5 — Fairness & Bias Evaluation (deterministic, in-boundary computation)."""
from __future__ import annotations


def evaluate(dataset_sample: list[dict], sensitive_features: list[str],
             fairness_threshold: float = 0.8) -> dict:
    metrics: dict = {}
    blockers: list[dict] = []
    worst_di = 1.0

    for feature in sensitive_features:
        groups: dict[str, dict] = {}
        for row in dataset_sample:
            value = str((row.get("attributes") or {}).get(feature, "unknown"))
            g = groups.setdefault(value, {"n": 0, "positive": 0, "label_pos": 0, "tp": 0})
            g["n"] += 1
            outcome = int(row.get("outcome", 0))
            g["positive"] += outcome
            if row.get("label") is not None:
                label = int(row["label"])
                g["label_pos"] += label
                if label == 1 and outcome == 1:
                    g["tp"] += 1

        selection_rates = {k: (g["positive"] / g["n"]) if g["n"] else 0.0
                           for k, g in groups.items()}
        rates = list(selection_rates.values())
        dp_diff = round(max(rates) - min(rates), 6) if rates else 0.0
        di_ratio = round(min(rates) / max(rates), 6) if rates and max(rates) > 0 else 1.0

        tprs = [g["tp"] / g["label_pos"] for g in groups.values() if g["label_pos"] > 0]
        eo_diff = round(max(tprs) - min(tprs), 6) if len(tprs) >= 2 else None

        metrics[feature] = {
            "demographicParityDifference": dp_diff,
            "disparateImpactRatio": di_ratio,
            "equalOpportunityDifference": eo_diff,
            "groupSelectionRates": {k: round(v, 6) for k, v in selection_rates.items()},
        }
        worst_di = min(worst_di, di_ratio)
        if di_ratio < fairness_threshold:
            blockers.append({
                "code": "DISPARATE_IMPACT", "framework": "EU-AI-ACT", "article": "Art. 10",
                "reason": (f"Disparate impact ratio {di_ratio} for '{feature}' is below the "
                           f"{fairness_threshold} threshold (four-fifths rule)."),
                "remediation": "Rebalance training data or apply bias mitigation, then re-run the evaluation."})

    articles = [
        {"framework": "EU-AI-ACT", "article": "Art. 10",
         "title": "Data and data governance (bias examination)"},
        {"framework": "GDPR", "article": "Art. 5",
         "title": "Fairness of processing (Art. 5(1)(a))"},
        {"framework": "NIST-AI-RMF", "article": "MEASURE 2.2",
         "title": "Fairness evaluation"},
    ]
    return {"metrics": metrics, "worstDisparateImpact": round(worst_di, 6),
            "threshold": fairness_threshold, "sampleSize": len(dataset_sample),
            "_articles": articles, "_blockers": blockers}
