"""Phase 0: store write/read integrity and append-only hash chaining."""

from __future__ import annotations

import os
import stat

from preflight.hashchain import GENESIS_PREV_HASH, link_hash
from preflight.store import Store


def test_write_then_read_round_trip(tmp_path):
    db = tmp_path / "audit.db"
    with Store(db) as store:
        store.append({"action": "a", "amount": 1})
        store.append({"action": "b", "amount": 2})
        rows = store.all_records()
    assert len(rows) == 2
    assert rows[0]["prev_hash"] == GENESIS_PREV_HASH
    # Second record chains onto the first.
    assert rows[1]["prev_hash"] == rows[0]["hash"]


def test_hash_field_matches_chain_formula(tmp_path):
    db = tmp_path / "audit.db"
    with Store(db) as store:
        store.append({"x": 1})
        rows = store.all_records()
    row = rows[0]
    assert row["hash"] == link_hash(row["prev_hash"], row["content_hash"])


def test_append_returns_hashes(tmp_path):
    db = tmp_path / "audit.db"
    with Store(db) as store:
        result = store.append({"x": 1})
    assert set(result) == {"prev_hash", "content_hash", "hash"}
    assert result["prev_hash"] == GENESIS_PREV_HASH


def test_no_mutation_api():
    # Append-only contract: the store must expose no update/delete methods.
    assert not hasattr(Store, "update")
    assert not hasattr(Store, "delete")


def test_db_permissions_are_restrictive(tmp_path):
    db = tmp_path / "audit.db"
    with Store(db) as store:
        store.append({"x": 1})
    mode = stat.S_IMODE(os.stat(db).st_mode)
    # No group/other read or write bits should be set where the OS enforces them.
    if os.name == "posix":
        assert mode & (stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH) == 0
