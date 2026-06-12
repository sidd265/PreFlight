"""Phase 5: audit export to JSON/Markdown/HTML, path-confined (S7)."""

from __future__ import annotations

import json

import pytest

from preflight.export import export_audit, write_export
from preflight.store import Store


def _records(tmp_path):
    store = Store(tmp_path / "p.db")
    store.append({"type": "decision", "action_id": "a1", "verdict": "allow"})
    store.append({"type": "decision", "action_id": "a2", "verdict": "block"})
    recs = store.all_records()
    store.close()
    return recs


def test_export_json_roundtrips(tmp_path):
    text = export_audit(_records(tmp_path), "json")
    data = json.loads(text)
    assert len(data) == 2
    assert data[0]["record"]["verdict"] == "allow"
    assert data[0]["hash"] and data[0]["content_hash"]


def test_export_markdown_and_html(tmp_path):
    recs = _records(tmp_path)
    md = export_audit(recs, "md")
    assert md.startswith("#") and "block" in md
    html = export_audit(recs, "html")
    assert "<table" in html and "block" in html


def test_export_rejects_unknown_format(tmp_path):
    with pytest.raises(ValueError):
        export_audit(_records(tmp_path), "pdf")


def test_write_export_confined_to_cwd(tmp_path, monkeypatch):
    recs = _records(tmp_path)
    workdir = tmp_path / "work"
    workdir.mkdir()
    monkeypatch.chdir(workdir)

    out = write_export(recs, "json", workdir / "out")
    assert out.exists()

    # Refuse to escape the working directory tree.
    with pytest.raises(ValueError):
        write_export(recs, "json", tmp_path.parent / "escape")
