"""SHA-256 hash-chain primitive for the tamper-evident audit log (CLAUDE.md §2).

Each record stores the previous record's `hash`, its own `content_hash`, and
`hash = sha256(prev_hash + content_hash)`. The genesis record uses a fixed,
documented `prev_hash`. There is NO function here that mutates a written record —
chaining and verifying only.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

# Fixed, documented genesis prev_hash. The first record in any chain links to this.
GENESIS_PREV_HASH = "0" * 64


def content_hash(payload: dict[str, Any]) -> str:
    """Stable SHA-256 of a record's content.

    Uses canonical JSON (sorted keys, no insignificant whitespace) so the same
    logical content always hashes identically regardless of dict ordering.
    """
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def link_hash(prev_hash: str, content_hash_value: str) -> str:
    """Chain hash binding a record to its predecessor: sha256(prev_hash + content_hash)."""
    return hashlib.sha256((prev_hash + content_hash_value).encode("utf-8")).hexdigest()


def compute_record_hashes(
    payload: dict[str, Any], prev_hash: str
) -> tuple[str, str]:
    """Return (content_hash, hash) for a new record chained onto `prev_hash`."""
    ch = content_hash(payload)
    return ch, link_hash(prev_hash, ch)
