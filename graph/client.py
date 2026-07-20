# SPDX-License-Identifier: Apache-2.0
"""Async Neo4j client for the governance control graph."""
from __future__ import annotations
import logging
import os
from pathlib import Path
from typing import Any, Optional
from neo4j import AsyncGraphDatabase, AsyncDriver

logger = logging.getLogger("graph.client")

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


class GraphClient:
    def __init__(self) -> None:
        self.driver: Optional[AsyncDriver] = None

    async def connect(self) -> None:
        self.driver = AsyncGraphDatabase.driver(
            os.environ.get("NEO4J_URI", "bolt://neo4j:7687"),
            auth=(os.environ.get("NEO4J_USER", "neo4j"),
                  os.environ.get("NEO4J_PASSWORD", "governance_secret")),
        )
        await self.driver.verify_connectivity()

    async def migrate(self) -> None:
        for path in sorted(MIGRATIONS_DIR.glob("*.cypher")):
            for stmt in path.read_text().split(";"):
                stmt = "\n".join(l for l in stmt.splitlines() if not l.strip().startswith("//")).strip()
                if stmt:
                    await self.run(stmt)
            logger.info("Applied graph migration %s", path.name)

    async def close(self) -> None:
        if self.driver:
            await self.driver.close()
            self.driver = None

    @property
    def available(self) -> bool:
        return self.driver is not None

    async def run(self, query: str, params: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
        if not self.driver:
            logger.warning("Neo4j unavailable — lineage write/read skipped")
            return []
        async with self.driver.session() as session:
            result = await session.run(query, params or {})
            return await result.data()


graph = GraphClient()
