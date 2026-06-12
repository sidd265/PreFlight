"""Audit-log verification (Phase 5, S4).

Recomputes the SHA-256 hash chain over the stored audit records and reports any
tampering: alteration of content, insertion, reorder, or deletion. Read-only — it
never mutates a record (the audit log is append-only).

How detection works:
  * content alteration -> recomputed content_hash != stored content_hash.
  * broken linkage (insertion / deletion / reorder) -> a record's prev_hash no longer
    equals the previous record's stored hash.
  * inconsistent record -> link_hash(prev_hash, content_hash) != stored hash.
"""

from __future__ import annotations

import json
import sqlite3

from pydantic import BaseModel, Field

from preflight.hashchain import GENESIS_PREV_HASH, content_hash, link_hash


class VerifyResult(BaseModel):
    ok: bool
    count: int
    problems: list[str] = Field(default_factory=list)
    first_bad_seq: int | None = None


def verify_chain(records: list[sqlite3.Row]) -> VerifyResult:
    """Verify a list of audit rows (in chain order). Returns a structured result."""
    problems: list[str] = []
    first_bad: int | None = None
    prev_hash = GENESIS_PREV_HASH

    def flag(seq: int, msg: str) -> None:
        nonlocal first_bad
        problems.append(f"seq {seq}: {msg}")
        if first_bad is None:
            first_bad = seq

    for row in records:
        seq = row["seq"]

        try:
            payload = json.loads(row["record_json"])
        except (ValueError, TypeError):
            flag(seq, "record_json is not valid JSON")
            prev_hash = row["hash"]
            continue

        if content_hash(payload) != row["content_hash"]:
            flag(seq, "content altered (content_hash mismatch)")

        if row["prev_hash"] != prev_hash:
            flag(seq, "broken chain link (prev_hash mismatch — insertion/deletion/reorder)")

        if link_hash(row["prev_hash"], row["content_hash"]) != row["hash"]:
            flag(seq, "hash inconsistent (link_hash mismatch)")

        prev_hash = row["hash"]

    return VerifyResult(
        ok=not problems, count=len(records), problems=problems, first_bad_seq=first_bad
    )
