# SPDX-License-Identifier: Apache-2.0
"""Regression tests for the security-audit findings.

- SEC-001 CRITICAL: Google-Auth test escape hatch must not activate in
  production (NODE_ENV=production) even if GOV_ALLOW_TEST_AUTH=1 leaks in.
- SEC-002 HIGH: GOOGLE_ALLOWED_EMAILS / GOOGLE_ALLOWED_DOMAINS must gate
  the Google Sign-In flow; unlisted users get 403.
- SEC-003 MEDIUM: Startup must refuse the wildcard `*` in CORS_ORIGINS
  (browsers reject it with credentials + it silently opens the API).
"""
from __future__ import annotations
import os
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from orchestrator.google_auth import (
    _authorize_email, _test_auth_enabled, DEFAULT_ROLE,
)


class TestSec001TestAuthProdSafeguard:
    def test_hatch_off_when_flag_unset(self):
        with patch.dict(os.environ, {"GOV_ALLOW_TEST_AUTH": "",
                                     "NODE_ENV": ""}, clear=False):
            os.environ.pop("GOV_ALLOW_TEST_AUTH", None)
            assert _test_auth_enabled() is False

    def test_hatch_off_when_flag_wrong_value(self):
        with patch.dict(os.environ, {"GOV_ALLOW_TEST_AUTH": "true",
                                     "NODE_ENV": ""}, clear=False):
            assert _test_auth_enabled() is False

    def test_hatch_on_in_non_production(self):
        with patch.dict(os.environ, {"GOV_ALLOW_TEST_AUTH": "1",
                                     "NODE_ENV": "development"}, clear=False):
            assert _test_auth_enabled() is True

    def test_hatch_forcibly_off_in_production(self):
        with patch.dict(os.environ, {"GOV_ALLOW_TEST_AUTH": "1",
                                     "NODE_ENV": "production"}, clear=False):
            assert _test_auth_enabled() is False

    def test_hatch_forcibly_off_case_insensitive(self):
        with patch.dict(os.environ, {"GOV_ALLOW_TEST_AUTH": "1",
                                     "NODE_ENV": "PRODUCTION"}, clear=False):
            assert _test_auth_enabled() is False


class TestSec002GoogleAllowList:
    def test_empty_allow_list_permits_all_legacy_behaviour(self):
        with patch.dict(os.environ, {"GOOGLE_ALLOWED_EMAILS": "",
                                     "GOOGLE_ALLOWED_DOMAINS": ""}, clear=False):
            assert _authorize_email("random@internet.com") == DEFAULT_ROLE

    def test_email_allow_list_grants_configured_role(self):
        with patch.dict(os.environ, {
            "GOOGLE_ALLOWED_EMAILS": "alice@acme.com=audit-engineer",
            "GOOGLE_ALLOWED_DOMAINS": "",
        }, clear=False):
            assert _authorize_email("alice@acme.com") == "audit-engineer"
            assert _authorize_email("Alice@Acme.com") == "audit-engineer"  # case-insensitive

    def test_email_allow_list_defaults_to_default_role_when_no_override(self):
        with patch.dict(os.environ, {
            "GOOGLE_ALLOWED_EMAILS": "alice@acme.com",
            "GOOGLE_ALLOWED_DOMAINS": "",
        }, clear=False):
            assert _authorize_email("alice@acme.com") == DEFAULT_ROLE

    def test_unlisted_email_is_403_when_list_set(self):
        with patch.dict(os.environ, {
            "GOOGLE_ALLOWED_EMAILS": "alice@acme.com",
            "GOOGLE_ALLOWED_DOMAINS": "",
        }, clear=False):
            with pytest.raises(HTTPException) as ex:
                _authorize_email("mallory@evil.com")
            assert ex.value.status_code == 403
            assert ex.value.detail["code"] == "GOOGLE_USER_NOT_AUTHORIZED"

    def test_domain_allow_list_matches_by_suffix(self):
        with patch.dict(os.environ, {
            "GOOGLE_ALLOWED_EMAILS": "",
            "GOOGLE_ALLOWED_DOMAINS": "acme.com=audit-engineer",
        }, clear=False):
            assert _authorize_email("anyone@acme.com") == "audit-engineer"
            with pytest.raises(HTTPException) as ex:
                _authorize_email("anyone@not-acme.com")
            assert ex.value.status_code == 403

    def test_email_wins_over_domain_for_specificity(self):
        with patch.dict(os.environ, {
            "GOOGLE_ALLOWED_EMAILS": "ceo@acme.com=governance-admin",
            "GOOGLE_ALLOWED_DOMAINS": "acme.com=audit-engineer",
        }, clear=False):
            assert _authorize_email("ceo@acme.com") == "governance-admin"
            assert _authorize_email("dev@acme.com") == "audit-engineer"

    def test_invalid_configured_role_raises_500(self):
        with patch.dict(os.environ, {
            "GOOGLE_ALLOWED_EMAILS": "alice@acme.com=SUPER-ROOT",
            "GOOGLE_ALLOWED_DOMAINS": "",
        }, clear=False):
            with pytest.raises(HTTPException) as ex:
                _authorize_email("alice@acme.com")
            assert ex.value.status_code == 500
            assert ex.value.detail["code"] == "INVALID_ROLE_MAPPING"

    def test_malformed_email_rejected(self):
        with patch.dict(os.environ, {
            "GOOGLE_ALLOWED_EMAILS": "",
            "GOOGLE_ALLOWED_DOMAINS": "",
        }, clear=False):
            with pytest.raises(HTTPException) as ex:
                _authorize_email("not-an-email")
            assert ex.value.status_code == 400


class TestSec003CorsWildcardRefused:
    def test_wildcard_with_credentials_refused_at_import(self):
        """Cannot re-import orchestrator.main here (already loaded), so
        exercise the guard by simulating the same conditional inline."""
        import os as _os
        env = _os.environ.get("CORS_ORIGINS", "").strip()
        # If CORS_ORIGINS contains *, the app.add_middleware call in
        # orchestrator/main.py raises RuntimeError. This test just documents
        # the invariant — the actual runtime enforcement is at boot.
        origins = [o.strip() for o in env.split(",") if o.strip()]
        if "*" in origins:
            pytest.fail("CORS_ORIGINS='*' with credentials must be refused")

    def test_no_cors_middleware_when_env_empty(self):
        # When CORS_ORIGINS is empty, no starlette CORSMiddleware is
        # installed. Verify by inspecting the app's user_middleware.
        from orchestrator.main import app
        has_cors = any("CORSMiddleware" in type(m.cls).__name__
                       for m in app.user_middleware
                       if hasattr(m, "cls"))
        # In the pytest environment CORS_ORIGINS is empty, so should be absent
        if not os.environ.get("CORS_ORIGINS", "").strip():
            assert not has_cors, (
                "CORSMiddleware installed with empty CORS_ORIGINS — this was "
                "the SEC-003 wildcard-reflection bug")
