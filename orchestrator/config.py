# SPDX-License-Identifier: Apache-2.0
"""Roles, scopes and service-account configuration (GOVERNANCE_AND_COMPLIANCE.md §3)."""
from __future__ import annotations
import os

PHASE_SCOPES = {
    "intake": "phase:intake",
    "scope": "phase:scope",
    "risk": "phase:risk",
    "data_protection": "phase:privacy",
    "fairness": "phase:fairness",
    "robustness": "phase:robustness",
    "explainability": "phase:explainability",
    "certification": "phase:certify",
    "monitoring": "phase:monitor",
}

ALL_SCOPES = sorted(set(PHASE_SCOPES.values()) | {"reaudit:trigger", "runs:read", "certs:read"})

ROLE_SCOPES = {
    "governance-admin": ALL_SCOPES,
    "intake-officer": ["phase:intake", "phase:scope", "runs:read"],
    "audit-engineer": ["phase:risk", "phase:privacy", "phase:fairness",
                       "phase:robustness", "phase:explainability", "runs:read"],
    "certification-officer": ["phase:certify", "phase:monitor", "reaudit:trigger",
                              "runs:read", "certs:read"],
}


def service_accounts() -> dict[str, dict]:
    return {
        "governance-admin": {
            "secret": os.environ.get("GOV_ADMIN_SECRET", "govern-admin-secret-dev"),
            "role": "governance-admin"},
        "intake-officer": {
            "secret": os.environ.get("GOV_INTAKE_SECRET", "intake-officer-secret-dev"),
            "role": "intake-officer"},
        "audit-engineer": {
            "secret": os.environ.get("GOV_AUDIT_SECRET", "audit-engineer-secret-dev"),
            "role": "audit-engineer"},
        "certification-officer": {
            "secret": os.environ.get("GOV_CERT_SECRET", "certification-officer-secret-dev"),
            "role": "certification-officer"},
    }


def jwt_secret() -> str:
    return os.environ.get("GOVERNANCE_JWT_SECRET", "governance-jwt-secret-dev")


def token_ttl_minutes() -> int:
    return int(os.environ.get("GOVERNANCE_TOKEN_TTL_MINUTES", "60"))


def status_base_url() -> str:
    return os.environ.get("GOVERNANCE_PUBLIC_BASE_URL", "http://localhost:8010").rstrip("/")
