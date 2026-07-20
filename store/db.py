# SPDX-License-Identifier: Apache-2.0
"""Async PostgreSQL pool + migration runner for the governance evidence store."""
from __future__ import annotations
import logging
import os
from pathlib import Path
from typing import Optional
import asyncpg

logger = logging.getLogger("store.db")

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


class GovernanceDB:
    def __init__(self) -> None:
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        self.pool = await asyncpg.create_pool(
            user=os.environ.get("POSTGRES_USER", "governance"),
            password=os.environ.get("POSTGRES_PASSWORD", "governance_secret"),
            database=os.environ.get("POSTGRES_DB", "evidence_store"),
            host=os.environ.get("POSTGRES_HOST", "postgres"),
            port=int(os.environ.get("POSTGRES_PORT", "5432")),
            min_size=2,
            max_size=10,
        )

    async def migrate(self) -> None:
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
                await conn.execute(path.read_text())
                logger.info("Applied migration %s", path.name)

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()
            self.pool = None


db = GovernanceDB()
