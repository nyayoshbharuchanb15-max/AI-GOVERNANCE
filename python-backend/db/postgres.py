"""
PostgreSQL Evidence Store — Async Database Client
───────────────────────────────────────────────────
ISO/IEC 42001:2023 Clause 7.5 mandates that all audit evidence
be retained as documented information. This module provides:

  - Connection pooling via asyncpg
  - JSONB storage for flexible audit log schemas
  - Full audit trail with timestamps and versioning

Tables:
  - audit_evidence: Flexible JSONB store for all audit artifacts
  - certificates: W3C Verifiable Credentials (VC-JSON)
  - drift_alerts: Time-series drift monitoring events

GDPR Art. 5(1)(e) — Storage limitation: retention policies are
enforced at the application layer.
"""

from __future__ import annotations
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
import asyncpg

logger = logging.getLogger("postgres")


class PostgresClient:
    """Async PostgreSQL client with JSONB support."""

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(
        self,
        user: str = "governance",
        password: str = "governance_secret",
        database: str = "evidence_store",
        host: str = "postgres",
        port: int = 5432,
    ) -> None:
        """Initialize connection pool."""
        self.pool = await asyncpg.create_pool(
            user=user,
            password=password,
            database=database,
            host=host,
            port=port,
            min_size=2,
            max_size=10,
        )

    async def close(self) -> None:
        """Close all connections."""
        if self.pool:
            await self.pool.close()

    async def store_evidence(
        self,
        model_id: str,
        audit_phase: str,
        payload: dict[str, Any],
        evidence_type: str = "audit_result",
    ) -> Optional[str]:
        """
        Store an audit artifact in the evidence store.

        Args:
            model_id: Unique model identifier
            audit_phase: Which phase generated this evidence
            payload: JSON-serializable audit result
            evidence_type: Type classification for the evidence

        Returns:
            evidence_id: UUID string, or None if the store is unavailable
        """
        if self.pool is None:
            logger.warning("PostgreSQL pool not available — cannot store evidence")
            return None
        evidence_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO audit_evidence (evidence_id, model_id, audit_phase,
                                                evidence_type, payload, created_at)
                    VALUES ($1, $2, $3, $4, $5::jsonb, $6)
                    """,
                    evidence_id,
                    model_id,
                    audit_phase,
                    evidence_type,
                    json.dumps(payload),
                    now,
                )
            return evidence_id
        except Exception:
            logger.exception("Failed to store evidence")
            return None

    async def get_evidence(self, evidence_id: str) -> Optional[dict[str, Any]]:
        """Retrieve an evidence record by ID."""
        if self.pool is None:
            logger.warning("PostgreSQL pool not available — cannot get evidence")
            return None
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM audit_evidence WHERE evidence_id = $1",
                    evidence_id,
                )
                return dict(row) if row else None
        except Exception:
            logger.exception("Failed to get evidence")
            return None

    async def store_certificate(
        self,
        model_id: str,
        vc_payload: dict[str, Any],
        evidence_id: str,
    ) -> None:
        """Store a W3C Verifiable Credential."""
        if self.pool is None:
            logger.warning("PostgreSQL pool not available — cannot store certificate")
            return
        now = datetime.now(timezone.utc).isoformat()
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO certificates (model_id, vc_payload, evidence_id, created_at)
                    VALUES ($1, $2::jsonb, $3, $4)
                    """,
                    model_id,
                    json.dumps(vc_payload),
                    evidence_id,
                    now,
                )
        except Exception:
            logger.exception("Failed to store certificate")

    async def store_drift_alert(
        self,
        model_id: str,
        metric: str,
        drift_score: float,
        threshold: float,
        status: str,
    ) -> None:
        """Log a drift monitoring event."""
        if self.pool is None:
            logger.warning("PostgreSQL pool not available — cannot store drift alert")
            return
        now = datetime.now(timezone.utc).isoformat()
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO drift_alerts (model_id, metric, drift_score,
                                              threshold, status, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    model_id,
                    metric,
                    drift_score,
                    threshold,
                    status,
                    now,
                )
        except Exception:
            logger.exception("Failed to store drift alert")

    async def store_pii_redaction_event(
        self,
        endpoint: str,
        redacted_fields: list[str],
        model_id: Optional[str] = None,
        request_path: Optional[str] = None,
    ) -> Optional[str]:
        """Log a PII redaction event (field names only — no PII values)."""
        if self.pool is None:
            logger.warning("PostgreSQL pool not available — cannot log PII redaction")
            return None
        event_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO pii_redactions (event_id, model_id, endpoint,
                                                 redacted_fields, redaction_count,
                                                 request_path, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    event_id,
                    model_id,
                    endpoint,
                    redacted_fields,
                    len(redacted_fields),
                    request_path,
                    now,
                )
            return event_id
        except Exception:
            logger.exception("Failed to log PII redaction event")
            return None

    async def get_audit_history(self, model_id: str) -> list[dict[str, Any]]:
        """Retrieve full audit history for a model."""
        if self.pool is None:
            logger.warning("PostgreSQL pool not available — cannot get audit history")
            return []
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT * FROM audit_evidence WHERE model_id = $1 ORDER BY created_at DESC",
                    model_id,
                )
                return [dict(row) for row in rows]
        except Exception:
            logger.exception("Failed to get audit history")
            return []


# Singleton instance
pg_client = PostgresClient()
