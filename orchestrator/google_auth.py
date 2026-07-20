# SPDX-License-Identifier: Apache-2.0
"""Emergent-managed Google Sign-In integration.

REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS,
THIS BREAKS THE AUTH.

Flow:
  1. Frontend redirects the browser to
     `https://auth.emergentagent.com/?redirect=<origin>/`.
  2. Emergent Auth returns the user to `<origin>/#session_id=<id>`.
  3. Frontend detects `session_id` in `window.location.hash` and calls
     `POST /api/v1/auth/google/session` with header `X-Session-ID: <id>`
     (and no body).
  4. This module calls
     `GET https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data`
     with the same header, receives
     `{id, email, name, picture, session_token}` from Emergent, persists a row
     in `governance_google_sessions`, sets an httpOnly cookie
     `governance_session` on the response, and returns a governance JWT bound
     to role `governance-admin` (per user's product decision).

`GET /api/v1/auth/me` and `POST /api/v1/auth/logout` are used by the SPA to
verify + clear the session respectively.
"""
from __future__ import annotations
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import HTTPException, Request, Response
from pydantic import BaseModel

from orchestrator.auth import JWT_ALGORITHM, JWT_ISSUER
from orchestrator.config import ROLE_SCOPES, jwt_secret, token_ttl_minutes
from store.db import db

import jwt as pyjwt

EMERGENT_SESSION_DATA_URL = (
    "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"
)
SESSION_COOKIE_NAME = "governance_session"
SESSION_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days
DEFAULT_ROLE = "governance-admin"


class GoogleSessionResponse(BaseModel):
    accessToken: str
    tokenType: str = "Bearer"
    expiresIn: int
    role: str
    scopes: list[str]
    clientId: str
    user: dict


# Testing-only escape hatch. Refuses to activate unless BOTH:
#   1. NODE_ENV is NOT "production" (production deployments never allow it).
#   2. GOV_ALLOW_TEST_AUTH == "1" is explicitly set.
# The fixture id must ALSO match GOOGLE_AUTH_TEST_SESSION_ID exactly. This
# stack of guards makes accidentally leaving the hatch on in prod impossible.
def _test_auth_enabled() -> bool:
    if os.environ.get("NODE_ENV", "").lower() == "production":
        return False
    return os.environ.get("GOV_ALLOW_TEST_AUTH") == "1"


async def _fetch_emergent_session(session_id: str) -> dict:
    """Look up the just-issued Emergent Auth session. One-shot lookup."""
    test_id = os.environ.get("GOOGLE_AUTH_TEST_SESSION_ID")
    test_tok = os.environ.get("GOOGLE_AUTH_TEST_SESSION_TOKEN")
    if _test_auth_enabled() and test_id and session_id == test_id:
        return {
            "id": "test-user",
            "email": os.environ.get(
                "GOOGLE_AUTH_TEST_EMAIL", "test.user@governance.local"),
            "name": "Test Governance User",
            "picture": "",
            "session_token": test_tok or f"test_{session_id}",
        }
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(
            EMERGENT_SESSION_DATA_URL,
            headers={"X-Session-ID": session_id},
        )
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail={
            "code": "GOOGLE_SESSION_INVALID",
            "message": "Emergent Auth session_id could not be exchanged",
        })
    data = r.json()
    for k in ("id", "email", "session_token"):
        if not data.get(k):
            raise HTTPException(status_code=502, detail={
                "code": "GOOGLE_SESSION_MALFORMED",
                "message": f"Missing '{k}' from Emergent Auth response",
            })
    return data


async def _persist_session(user: dict, role: str) -> datetime:
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=SESSION_TTL_SECONDS)
    assert db.pool is not None
    async with db.pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO governance_google_sessions
                (session_token, user_id, email, name, picture, role, expires_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7)
            ON CONFLICT (session_token) DO UPDATE
              SET user_id=EXCLUDED.user_id, email=EXCLUDED.email,
                  name=EXCLUDED.name, picture=EXCLUDED.picture,
                  role=EXCLUDED.role, expires_at=EXCLUDED.expires_at
            """,
            user["session_token"], user["id"], user["email"],
            user.get("name"), user.get("picture"), role, expires_at,
        )
    return expires_at


def _mint_governance_jwt(email: str, role: str) -> tuple[str, int, list[str]]:
    scopes = ROLE_SCOPES[role]
    ttl_seconds = token_ttl_minutes() * 60
    now = datetime.now(timezone.utc)
    token = pyjwt.encode(
        {
            "sub": f"google:{email}",
            "role": role,
            "scopes": scopes,
            "type": "access",
            "iss": JWT_ISSUER,
            "iat": now,
            "exp": now + timedelta(seconds=ttl_seconds),
        },
        jwt_secret(),
        algorithm=JWT_ALGORITHM,
    )
    return token, ttl_seconds, scopes


def _authorize_email(email: str) -> str:
    """Enforce the operator-configured email/domain allow-list.

    Returns the role to mint. Raises HTTPException(403) if the user is not
    on the list.

    Env var contract (both optional; if both empty, the legacy permissive
    behaviour applies — every Google user is minted DEFAULT_ROLE — with a
    startup warning emitted from validate_startup_config()):

      GOOGLE_ALLOWED_EMAILS   comma-separated exact addresses, each optionally
                              followed by "=<role>" to override the role.
                              Example: "alice@acme.com=governance-admin,bob@acme.com=audit-engineer"
      GOOGLE_ALLOWED_DOMAINS  comma-separated domain suffixes, each optionally
                              followed by "=<role>".
                              Example: "acme.com=audit-engineer"

    Lookup order: exact-email first, then domain match. Unmatched addresses
    are refused when either list is non-empty.
    """
    email_norm = email.strip().lower()
    if not email_norm or "@" not in email_norm:
        raise HTTPException(status_code=400, detail={
            "code": "MALFORMED_EMAIL",
            "message": "Emergent Auth returned an unparseable email",
        })
    domain = email_norm.rsplit("@", 1)[1]

    def _parse_list(raw: str) -> dict[str, str]:
        out: dict[str, str] = {}
        for entry in raw.split(","):
            entry = entry.strip().lower()
            if not entry:
                continue
            key, _, role = entry.partition("=")
            out[key.strip()] = (role.strip() or DEFAULT_ROLE)
        return out

    emails = _parse_list(os.environ.get("GOOGLE_ALLOWED_EMAILS", ""))
    domains = _parse_list(os.environ.get("GOOGLE_ALLOWED_DOMAINS", ""))

    if not emails and not domains:
        # Legacy permissive mode. A startup warning is emitted elsewhere.
        return DEFAULT_ROLE

    if email_norm in emails:
        role = emails[email_norm]
    elif domain in domains:
        role = domains[domain]
    else:
        raise HTTPException(status_code=403, detail={
            "code": "GOOGLE_USER_NOT_AUTHORIZED",
            "message": (f"'{email}' is not on the Google-Auth allow-list. "
                        "Contact an administrator to be added."),
        })
    if role not in ROLE_SCOPES:
        raise HTTPException(status_code=500, detail={
            "code": "INVALID_ROLE_MAPPING",
            "message": f"Configured role '{role}' is not a known governance role",
        })
    return role


async def exchange_google_session(request: Request, response: Response) -> dict:
    session_id = request.headers.get("X-Session-ID") or request.headers.get(
        "x-session-id")
    if not session_id:
        raise HTTPException(status_code=400, detail={
            "code": "MISSING_SESSION_ID",
            "message": "X-Session-ID header is required",
        })
    user = await _fetch_emergent_session(session_id)
    role = _authorize_email(user["email"])
    expires_at = await _persist_session(user, role)
    access_token, ttl, scopes = _mint_governance_jwt(user["email"], role)

    response.set_cookie(
        SESSION_COOKIE_NAME,
        user["session_token"],
        max_age=SESSION_TTL_SECONDS,
        path="/",
        httponly=True,
        secure=True,
        samesite="none",
    )
    return {
        "accessToken": access_token,
        "tokenType": "Bearer",
        "expiresIn": ttl,
        "role": role,
        "scopes": scopes,
        "clientId": f"google:{user['email']}",
        "user": {
            "email": user["email"],
            "name": user.get("name") or "",
            "picture": user.get("picture") or "",
            "userId": user["id"],
            "expiresAt": expires_at.isoformat(),
        },
    }


async def _lookup_session(session_token: str) -> Optional[dict]:
    assert db.pool is not None
    async with db.pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT user_id, email, name, picture, role, expires_at "
            "FROM governance_google_sessions WHERE session_token=$1",
            session_token,
        )
    if not row:
        return None
    expires_at = row["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None
    return {
        "userId": row["user_id"],
        "email": row["email"],
        "name": row["name"] or "",
        "picture": row["picture"] or "",
        "role": row["role"],
        "expiresAt": expires_at.isoformat(),
    }


async def get_me(request: Request) -> dict:
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            session_token = auth[7:]
    if not session_token:
        raise HTTPException(status_code=401, detail={
            "code": "NOT_AUTHENTICATED",
            "message": "No governance_session cookie or Bearer token",
        })
    user = await _lookup_session(session_token)
    if not user:
        raise HTTPException(status_code=401, detail={
            "code": "SESSION_EXPIRED",
            "message": "Session missing or expired",
        })
    user["scopes"] = ROLE_SCOPES[user["role"]]
    return user


async def logout(request: Request, response: Response) -> Response:
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if session_token:
        assert db.pool is not None
        async with db.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM governance_google_sessions WHERE session_token=$1",
                session_token,
            )
    response.delete_cookie(SESSION_COOKIE_NAME, path="/", samesite="none", secure=True)
    response.status_code = 204
    return response
