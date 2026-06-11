"""SQLite store for Preflight (CLAUDE.md §1 code-level security).

- Parameterized SQL only — never string-built queries.
- Restrictive file permissions (0600) on the DB file.
- Append-only for audit records: write and read, no update/delete API.
"""

from __future__ import annotations

import json
import os
import sqlite3
import stat
from pathlib import Path
from typing import Any

from preflight.hashchain import GENESIS_PREV_HASH, compute_record_hashes


def _restrict_permissions(path: Path) -> None:
    """Set 0600 on the file. No-op tolerated on platforms without POSIX perms,
    but we always attempt it."""
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except (OSError, NotImplementedError):
        # On some Windows configs chmod is limited; the file is still user-scoped.
        pass


class Store:
    """Local SQLite-backed store. Holds the append-only audit chain of decisions."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        new_file = not self.db_path.exists()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        if new_file:
            _restrict_permissions(self.db_path)
        self._init_schema()
        _restrict_permissions(self.db_path)

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_records (
                seq          INTEGER PRIMARY KEY AUTOINCREMENT,
                record_json  TEXT NOT NULL,
                prev_hash    TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                hash         TEXT NOT NULL
            )
            """
        )
        # Recording tables (Phase 1). These hold redacted recorded actions grouped
        # into runs. Unlike audit_records they are working data, not the audit chain.
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id     TEXT PRIMARY KEY,
                name       TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recorded_actions (
                seq          INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id       TEXT NOT NULL,
                action_json  TEXT NOT NULL,
                outcome      TEXT NOT NULL,
                fingerprint  TEXT NOT NULL,
                cost_usd     REAL NOT NULL,
                FOREIGN KEY (run_id) REFERENCES runs(run_id)
            )
            """
        )
        self._conn.commit()

    # --- Recording (Phase 1) ------------------------------------------------

    def create_run(self, run_id: str, name: str, created_at: str) -> None:
        self._conn.execute(
            "INSERT INTO runs (run_id, name, created_at) VALUES (?, ?, ?)",
            (run_id, name, created_at),
        )
        self._conn.commit()

    def add_recorded_action(
        self,
        run_id: str,
        action_json: str,
        outcome: str,
        fingerprint: str,
        cost_usd: float,
    ) -> None:
        """Persist one recorded action. `action_json` must already be REDACTED."""
        self._conn.execute(
            "INSERT INTO recorded_actions "
            "(run_id, action_json, outcome, fingerprint, cost_usd) VALUES (?, ?, ?, ?, ?)",
            (run_id, action_json, outcome, fingerprint, cost_usd),
        )
        self._conn.commit()

    def actions_for_run(self, run_id: str) -> list[sqlite3.Row]:
        cur = self._conn.execute(
            "SELECT seq, run_id, action_json, outcome, fingerprint, cost_usd "
            "FROM recorded_actions WHERE run_id = ? ORDER BY seq ASC",
            (run_id,),
        )
        return cur.fetchall()

    def latest_run(self) -> sqlite3.Row | None:
        cur = self._conn.execute(
            "SELECT run_id, name, created_at FROM runs ORDER BY created_at DESC, rowid DESC LIMIT 1"
        )
        return cur.fetchone()

    def get_run(self, run_id: str) -> sqlite3.Row | None:
        cur = self._conn.execute(
            "SELECT run_id, name, created_at FROM runs WHERE run_id = ?", (run_id,)
        )
        return cur.fetchone()

    def all_runs(self) -> list[sqlite3.Row]:
        cur = self._conn.execute(
            "SELECT run_id, name, created_at FROM runs ORDER BY created_at ASC, rowid ASC"
        )
        return cur.fetchall()

    # --- Audit chain --------------------------------------------------------

    def last_hash(self) -> str:
        """Hash of the most recent record, or the genesis hash if the chain is empty."""
        cur = self._conn.execute(
            "SELECT hash FROM audit_records ORDER BY seq DESC LIMIT 1"
        )
        row = cur.fetchone()
        return row["hash"] if row else GENESIS_PREV_HASH

    def append(self, record: dict[str, Any]) -> dict[str, str]:
        """Append a record to the chain. `record` must already be REDACTED.

        Returns the computed {prev_hash, content_hash, hash}. Append-only:
        there is intentionally no update or delete method.
        """
        prev_hash = self.last_hash()
        ch, h = compute_record_hashes(record, prev_hash)
        self._conn.execute(
            "INSERT INTO audit_records (record_json, prev_hash, content_hash, hash) "
            "VALUES (?, ?, ?, ?)",
            (json.dumps(record, sort_keys=True, default=str), prev_hash, ch, h),
        )
        self._conn.commit()
        return {"prev_hash": prev_hash, "content_hash": ch, "hash": h}

    def all_records(self) -> list[sqlite3.Row]:
        """Return every audit row in chain order (oldest first)."""
        cur = self._conn.execute(
            "SELECT seq, record_json, prev_hash, content_hash, hash "
            "FROM audit_records ORDER BY seq ASC"
        )
        return cur.fetchall()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> Store:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
