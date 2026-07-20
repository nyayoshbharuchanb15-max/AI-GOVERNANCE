# SPDX-License-Identifier: Apache-2.0
"""Canonical JSON + deterministic integrity hashing (ARCHITECTURE.md §4.2)."""
from __future__ import annotations
import hashlib
import json
from typing import Any


def canonical_json(obj: Any) -> str:
    """JCS-style canonical JSON: sorted keys, no whitespace, UTF-8."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def integrity_hash(run_id: str, phase: str, control_version: str,
                   inputs: dict, outputs: dict, prev_hash: str) -> str:
    payload = {
        "run_id": run_id,
        "phase": phase,
        "control_version": control_version,
        "inputs": inputs,
        "outputs": outputs,
        "prev_hash": prev_hash,
    }
    return "sha256:" + sha256_hex(canonical_json(payload))


def run_genesis_hash(run_id: str) -> str:
    return "sha256:" + sha256_hex(run_id)
