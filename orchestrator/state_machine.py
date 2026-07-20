# SPDX-License-Identifier: Apache-2.0
"""Deterministic phase state machine (ARCHITECTURE.md §5)."""
from __future__ import annotations

PHASE_ORDER = ["intake", "scope", "risk", "data_protection", "fairness",
               "robustness", "explainability", "certification", "monitoring"]

PHASE_NUMBERS = {key: i + 1 for i, key in enumerate(PHASE_ORDER)}

DEPENDENCIES: dict[str, list[str]] = {
    "intake": [],
    "scope": ["intake"],
    "risk": ["scope"],
    "data_protection": ["risk"],
    "fairness": ["risk"],
    "robustness": ["risk"],
    "explainability": ["risk"],
    "certification": ["data_protection", "fairness", "robustness", "explainability"],
    "monitoring": ["certification"],
}


class PipelineError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 409) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def ensure_can_execute(run: dict, results: list[dict], phase_key: str) -> None:
    if run["status"] == "blocked":
        if phase_key == "certification":
            raise PipelineError(
                "CERTIFICATION_BLOCKED",
                "A blocker finding halted this run; certificate issuance is prohibited.")
        raise PipelineError(
            "RUN_BLOCKED",
            "This run was halted by a blocker finding; no further phases may execute.")
    done = {r["phase_key"]: r for r in results}
    if phase_key in done:
        raise PipelineError(
            "PHASE_ALREADY_EXECUTED",
            f"Phase '{phase_key}' already executed for this run; reaudits create a new run.")
    missing = [dep for dep in DEPENDENCIES[phase_key]
               if done.get(dep, {}).get("status") != "passed"]
    if missing:
        raise PipelineError(
            "PRECONDITION_NOT_MET",
            f"Phase '{phase_key}' requires passed prerequisite phase(s): {', '.join(missing)}.")
