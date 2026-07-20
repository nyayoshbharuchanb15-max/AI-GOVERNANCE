# SPDX-License-Identifier: Apache-2.0
"""Redis Streams fabric: ordered publish, consumer groups, idempotent retry, dead-letter.

Streams (all internal-only — no public endpoints):
  governance:phase-events  — phase completion envelopes
  governance:reaudit       — reaudit trigger requests
  governance:dead-letter   — envelopes that failed MAX_ATTEMPTS deliveries
"""
from __future__ import annotations
import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Optional
import redis.asyncio as aioredis

logger = logging.getLogger("events.fabric")

PHASE_EVENTS_STREAM = "governance:phase-events"
REAUDIT_STREAM = "governance:reaudit"
DEAD_LETTER_STREAM = "governance:dead-letter"
MAX_ATTEMPTS = 3
PROCESSED_TTL_SECONDS = 7 * 24 * 3600


def deterministic_event_id(*parts: str) -> str:
    return hashlib.sha256(":".join(parts).encode()).hexdigest()[:32]


class EventFabric:
    def __init__(self) -> None:
        self.client: Optional[aioredis.Redis] = None
        self._tasks: list[asyncio.Task] = []

    async def connect(self) -> None:
        self.client = aioredis.from_url(
            os.environ.get("REDIS_URL", "redis://redis:6379/0"), decode_responses=True)
        await self.client.ping()

    async def close(self) -> None:
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()
        if self.client:
            await self.client.aclose()
            self.client = None

    @property
    def available(self) -> bool:
        return self.client is not None

    # ─── Publish ─────────────────────────────────────────────────

    async def publish(self, stream: str, event_type: str, payload: dict[str, Any],
                      event_id: Optional[str] = None) -> Optional[str]:
        if not self.client:
            logger.warning("Redis unavailable — event %s not published", event_type)
            return None
        event_id = event_id or deterministic_event_id(
            event_type, json.dumps(payload, sort_keys=True))
        envelope = {
            "eventId": event_id,
            "type": event_type,
            "occurredAt": datetime.now(timezone.utc).isoformat(),
            "payload": json.dumps(payload),
        }
        await self.client.xadd(stream, envelope)
        return event_id

    async def publish_phase_event(self, run_id: str, phase: str, status: str,
                                  integrity_hash: str, extra: Optional[dict] = None) -> Optional[str]:
        event_id = deterministic_event_id(run_id, phase, integrity_hash)
        return await self.publish(
            PHASE_EVENTS_STREAM,
            f"phase.{status}",
            {"runId": run_id, "phase": phase, "status": status,
             "integrityHash": integrity_hash, **(extra or {})},
            event_id=event_id)

    async def publish_reaudit_trigger(self, model_id: str, trigger: dict[str, Any]) -> Optional[str]:
        return await self.publish(
            REAUDIT_STREAM, "reaudit.triggered", {"modelId": model_id, "trigger": trigger})

    # ─── Consume (idempotent, retry-safe, dead-letter) ───────────

    async def _is_processed(self, group: str, event_id: str) -> bool:
        return bool(await self.client.sismember(f"governance:processed:{group}", event_id))

    async def _mark_processed(self, group: str, event_id: str) -> None:
        key = f"governance:processed:{group}"
        await self.client.sadd(key, event_id)
        await self.client.expire(key, PROCESSED_TTL_SECONDS)

    async def _dead_letter(self, stream: str, group: str, entry_id: str,
                           fields: dict, attempts: int, error: str) -> None:
        await self.client.xadd(DEAD_LETTER_STREAM, {
            **fields, "sourceStream": stream, "attempts": str(attempts), "lastError": error[:500]})
        await self.client.xack(stream, group, entry_id)
        logger.error("Dead-lettered %s from %s after %d attempts: %s",
                     fields.get("eventId"), stream, attempts, error)

    async def _handle_entry(self, stream: str, group: str, entry_id: str, fields: dict,
                            attempts: int, handler: Callable[[dict], Awaitable[None]]) -> None:
        event_id = fields.get("eventId", entry_id)
        if await self._is_processed(group, event_id):
            await self.client.xack(stream, group, entry_id)  # idempotent skip
            return
        try:
            envelope = {**fields, "payload": json.loads(fields.get("payload", "{}")),
                        "attempt": attempts}
            await handler(envelope)
            await self._mark_processed(group, event_id)
            await self.client.xack(stream, group, entry_id)
        except Exception as exc:
            if attempts >= MAX_ATTEMPTS:
                await self._dead_letter(stream, group, entry_id, fields, attempts, str(exc))
            else:
                logger.warning("Handler failed (attempt %d/%d) for %s: %s",
                               attempts, MAX_ATTEMPTS, event_id, exc)
                # leave pending — reclaimed by the retry sweep

    async def _consume_loop(self, stream: str, group: str, consumer: str,
                            handler: Callable[[dict], Awaitable[None]]) -> None:
        try:
            await self.client.xgroup_create(stream, group, id="0", mkstream=True)
        except aioredis.ResponseError:
            pass
        while True:
            try:
                # retry sweep: reclaim pending entries (idle > 2s), attempt = delivery count
                pending = await self.client.xpending_range(stream, group, "-", "+", 20)
                for p in pending:
                    if p["time_since_delivered"] < 2000:
                        continue
                    claimed = await self.client.xclaim(
                        stream, group, consumer, min_idle_time=2000, message_ids=[p["message_id"]])
                    for entry_id, fields in claimed:
                        await self._handle_entry(stream, group, entry_id, fields,
                                                 p["times_delivered"], handler)
                messages = await self.client.xreadgroup(
                    group, consumer, {stream: ">"}, count=10, block=2000)
                for _stream, entries in messages or []:
                    for entry_id, fields in entries:
                        await self._handle_entry(stream, group, entry_id, fields, 1, handler)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Consumer loop error on %s", stream)
                await asyncio.sleep(1)

    def start_consumer(self, stream: str, group: str, consumer: str,
                       handler: Callable[[dict], Awaitable[None]]) -> None:
        self._tasks.append(asyncio.create_task(
            self._consume_loop(stream, group, consumer, handler)))

    # ─── Introspection ───────────────────────────────────────────

    async def read_dead_letters(self, limit: int = 50) -> list[dict]:
        if not self.client:
            return []
        entries = await self.client.xrevrange(DEAD_LETTER_STREAM, count=limit)
        return [{"entryId": eid, **fields} for eid, fields in entries]


fabric = EventFabric()
