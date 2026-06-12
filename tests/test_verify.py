"""Phase 5: audit-log verification detects tampering (S4).

The chain must catch alteration, insertion, reorder, and deletion. Tests simulate an
attacker by mutating the SQLite file DIRECTLY (the Store has no update/delete API).
"""

from __future__ import annotations

import sqlite3

from preflight.store import Store
from preflight.verify import verify_chain


def _seed_chain(db) -> Store:
    store = Store(db)
    store.append({"type": "decision", "action_id": "a1", "verdict": "allow"})
    store.append({"type": "decision", "action_id": "a2", "verdict": "needs_approval"})
    store.append({"type": "decision", "action_id": "a3", "verdict": "block"})
    return store


def test_clean_chain_verifies(tmp_path):
    store = _seed_chain(tmp_path / "p.db")
    result = verify_chain(store.all_records())
    store.close()
    assert result.ok
    assert result.count == 3
    assert result.first_bad_seq is None


def test_detects_alteration(tmp_path):
    db = tmp_path / "p.db"
    store = _seed_chain(db)
    store.close()
    # Attacker edits a record's content in place, leaving the stored hashes alone.
    con = sqlite3.connect(str(db))
    con.execute(
        "UPDATE audit_records SET record_json = ? WHERE seq = 2",
        ('{"type":"decision","action_id":"a2","verdict":"allow"}',),  # flipped to allow
    )
    con.commit()
    con.close()

    store = Store(db)
    result = verify_chain(store.all_records())
    store.close()
    assert not result.ok
    assert result.first_bad_seq == 2


def test_detects_deletion(tmp_path):
    db = tmp_path / "p.db"
    store = _seed_chain(db)
    store.close()
    con = sqlite3.connect(str(db))
    con.execute("DELETE FROM audit_records WHERE seq = 2")  # remove the middle record
    con.commit()
    con.close()

    store = Store(db)
    result = verify_chain(store.all_records())
    store.close()
    assert not result.ok  # record 3's prev_hash no longer matches record 1's hash


def test_detects_reorder(tmp_path):
    db = tmp_path / "p.db"
    store = _seed_chain(db)
    store.close()
    con = sqlite3.connect(str(db))
    # Swap the seq numbers of records 2 and 3 (reorder).
    con.execute("UPDATE audit_records SET seq = 99 WHERE seq = 2")
    con.execute("UPDATE audit_records SET seq = 2 WHERE seq = 3")
    con.execute("UPDATE audit_records SET seq = 3 WHERE seq = 99")
    con.commit()
    con.close()

    store = Store(db)
    result = verify_chain(store.all_records())
    store.close()
    assert not result.ok


def test_detects_insertion(tmp_path):
    db = tmp_path / "p.db"
    store = _seed_chain(db)
    store.close()
    con = sqlite3.connect(str(db))
    # Shift originals down, then forge a record into the gap at seq 2 (insertion).
    con.execute("UPDATE audit_records SET seq = seq + 10 WHERE seq >= 2")
    forged = '{"type":"decision","action_id":"forged","verdict":"allow"}'
    con.execute(
        "INSERT INTO audit_records (seq, record_json, prev_hash, content_hash, hash) "
        "VALUES (?, ?, ?, ?, ?)",
        (2, forged, "x" * 64, "y" * 64, "z" * 64),
    )
    con.commit()
    con.close()

    store = Store(db)
    result = verify_chain(store.all_records())
    store.close()
    assert not result.ok
