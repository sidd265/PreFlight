"""Audit-log export (Phase 5): JSON / Markdown / HTML.

Read-only rendering of the append-only audit chain. Output paths are confined to the
current working directory tree (no traversal, S7). Each record's hashes are included
so an exported trail can be independently re-verified.
"""

from __future__ import annotations

import html
import json
import os
import sqlite3
from pathlib import Path

_EXTENSIONS = {"json": "json", "md": "md", "markdown": "md", "html": "html"}


def _rows_to_dicts(records: list[sqlite3.Row]) -> list[dict]:
    out = []
    for r in records:
        try:
            record = json.loads(r["record_json"])
        except (ValueError, TypeError):
            record = {"_raw": r["record_json"]}
        out.append(
            {
                "seq": r["seq"],
                "record": record,
                "prev_hash": r["prev_hash"],
                "content_hash": r["content_hash"],
                "hash": r["hash"],
            }
        )
    return out


def export_audit(records: list[sqlite3.Row], fmt: str) -> str:
    """Render the audit chain as a string in the given format."""
    key = fmt.lower()
    if key not in _EXTENSIONS:
        raise ValueError(f"unknown export format: {fmt!r} (use json | md | html)")
    items = _rows_to_dicts(records)

    if key == "json":
        return json.dumps(items, indent=2, sort_keys=True, default=str)

    if _EXTENSIONS[key] == "md":
        lines = ["# Preflight Audit Trail", "", f"{len(items)} record(s), hash-chained.", ""]
        lines.append("| Seq | Record | Hash (first 12) |")
        lines.append("| --- | --- | --- |")
        for it in items:
            rec = json.dumps(it["record"], sort_keys=True, default=str)
            lines.append(f"| {it['seq']} | `{rec}` | `{it['hash'][:12]}…` |")
        return "\n".join(lines) + "\n"

    # html
    body = []
    for it in items:
        rec = html.escape(json.dumps(it["record"], sort_keys=True, default=str))
        body.append(
            f"<tr><td>{it['seq']}</td><td><code>{rec}</code></td>"
            f"<td><code>{html.escape(it['hash'][:12])}…</code></td></tr>"
        )
    rows_html = "\n".join(body)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Preflight Audit Trail</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #1f2328; }}
  table {{ border-collapse: collapse; margin-top: 1rem; }}
  th, td {{ border: 1px solid #d0d7de; padding: 0.4rem 0.7rem; font-size: 0.9rem; }}
  th {{ background: #f6f8fa; text-align: left; }}
  code {{ font-size: 0.8rem; }}
</style></head><body>
<h1>Preflight Audit Trail</h1>
<p>{len(items)} record(s), SHA-256 hash-chained &amp; tamper-evident.</p>
<table>
  <tr><th>Seq</th><th>Record</th><th>Hash</th></tr>
  {rows_html}
</table>
</body></html>
"""


def write_export(records: list[sqlite3.Row], fmt: str, out_dir: str | Path) -> Path:
    """Write the export to ``out_dir/audit.<ext>``, confined to the working directory."""
    key = fmt.lower()
    if key not in _EXTENSIONS:
        raise ValueError(f"unknown export format: {fmt!r} (use json | md | html)")

    out_dir = Path(out_dir).resolve()
    cwd = Path.cwd().resolve()
    if not (out_dir == cwd or str(out_dir).startswith(str(cwd) + os.sep)):
        raise ValueError("refusing to write export outside the working directory")

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"audit.{_EXTENSIONS[key]}"
    out_path.write_text(export_audit(records, fmt), encoding="utf-8")
    return out_path
