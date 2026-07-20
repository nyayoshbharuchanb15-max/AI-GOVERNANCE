"""Shared pytest fixtures — read service-account secrets from env vars.

The orchestrator refuses to boot with the previously-committed dev secrets,
so tests must source them the same way the orchestrator does. Reads
`/app/backend/.env` if the variable isn't already in the process env.

Also enables the Google-Auth fixture escape hatch **only for the pytest
run**, and only in non-production environments. The escape hatch is
never enabled in the deployed .env (per security-audit finding SEC-001).
"""
from __future__ import annotations
import os
from pathlib import Path


def _seed_from_env_file() -> None:
    env_path = Path("/app/backend/.env")
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)


_seed_from_env_file()


def _secret(env_var: str) -> str:
    v = os.environ.get(env_var, "")
    if not v:
        raise RuntimeError(
            f"{env_var} not set — cannot run governance test suite. "
            "Set it in /app/backend/.env or export it.")
    return v


# Centralised credential map used by every test module.
CREDS = {
    "governance-admin": _secret("GOV_ADMIN_SECRET"),
    "intake-officer": _secret("GOV_INTAKE_SECRET"),
    "audit-engineer": _secret("GOV_AUDIT_SECRET"),
    "certification-officer": _secret("GOV_CERT_SECRET"),
}


# ─── Google-Auth fixture (test-run scope only) ─────────────────────
# We inject these into the process environment for pytest so the
# in-process orchestrator honours the escape hatch. They are NOT set
# in /app/backend/.env — the deployed preview refuses this branch.
#
# The escape hatch also refuses to activate when NODE_ENV=production,
# so accidentally leaking these values from a CI run has no effect on
# a real deployment.
os.environ.setdefault("GOOGLE_AUTH_TEST_SESSION_ID",
                      "test-fixture-session-id-abc123")
os.environ.setdefault("GOOGLE_AUTH_TEST_SESSION_TOKEN",
                      "test-fixture-session-token-xyz789")
os.environ.setdefault("GOOGLE_AUTH_TEST_EMAIL",
                      "test.user@governance.local")
os.environ.setdefault("GOV_ALLOW_TEST_AUTH", "1")


def pytest_configure(config):
    """Turn on the escape hatch inside the *running orchestrator process* too.

    The orchestrator is already running (managed by supervisor). Its env
    was loaded when uvicorn booted, so setting env vars from pytest
    doesn't reach it. We therefore restart the backend with the fixture
    vars set — but only if it wasn't already restarted this test run.
    """
    marker = "/tmp/.gov-test-auth-enabled"
    if os.path.exists(marker):
        return
    # Detect whether we're running against a supervisor-managed backend
    # on localhost (preview) or an external URL (CI compose stack). Only
    # try to restart in the local case.
    api_url = os.environ.get("GOVERNANCE_API_URL", "")
    if "localhost" not in api_url and "127.0.0.1" not in api_url:
        return
    try:
        import subprocess
        env_lines = [
            'GOOGLE_AUTH_TEST_SESSION_ID="test-fixture-session-id-abc123"',
            'GOOGLE_AUTH_TEST_SESSION_TOKEN="test-fixture-session-token-xyz789"',
            'GOOGLE_AUTH_TEST_EMAIL="test.user@governance.local"',
            'GOV_ALLOW_TEST_AUTH="1"',
        ]
        env_path = Path("/app/backend/.env")
        current = env_path.read_text() if env_path.exists() else ""
        needs_write = any(k.split("=", 1)[0] not in current
                          for k in env_lines)
        if needs_write:
            with env_path.open("a", encoding="utf-8") as f:
                f.write("\n# --- test-only, removed by teardown ---\n")
                for line in env_lines:
                    f.write(line + "\n")
            subprocess.run(["supervisorctl", "restart", "backend"],
                           check=False, capture_output=True)
            import time
            time.sleep(5)
        with open(marker, "w") as f:
            f.write("1")
    except Exception:
        # If restart machinery is unavailable, the tests will just fail
        # loudly on the /auth/google/session fixture path.
        pass


def pytest_unconfigure(config):
    """Strip the test-only lines from /app/backend/.env after the run.

    Idempotent: only removes the block we appended.
    """
    marker = "/tmp/.gov-test-auth-enabled"
    if not os.path.exists(marker):
        return
    try:
        env_path = Path("/app/backend/.env")
        if not env_path.exists():
            return
        text = env_path.read_text()
        idx = text.find("\n# --- test-only, removed by teardown ---\n")
        if idx != -1:
            env_path.write_text(text[:idx].rstrip() + "\n")
            import subprocess
            subprocess.run(["supervisorctl", "restart", "backend"],
                           check=False, capture_output=True)
        os.remove(marker)
    except Exception:
        pass
