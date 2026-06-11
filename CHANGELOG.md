# Changelog

All notable changes to Preflight are documented here.

## [Unreleased]

### Phase 1 — Recording + Waste Report
- Recording SDK (`Recorder`): context manager + decorator that capture actions
  **through the redaction pass** before persisting — raw secrets never stored.
- Per-model token→cost pricing (`pricing.py`); cost captured on every action.
- Waste detection (`waste.py`): flags duplicates/loops, no-ops, and errors;
  totals wasted spend and ratio.
- `preflight report`: waste & ROI report in terminal text (Rich) and
  self-contained HTML (`--html`, path-confined to the working directory).
- Sample agent fixture (`examples/sample_agent.py`) with a planted fake API key —
  the fixture every later phase tests against.
- Store extended with `runs` / `recorded_actions` tables (parameterized SQL).

### Phase 0 — Scaffold & Schema
- Project packaging (`pyproject.toml`), uv-managed, pinned to Python 3.12.
- Core Pydantic v2 schemas: `Context`, `Action`, `Decision`, `Waste`.
- SHA-256 hash-chain primitive for the tamper-evident audit log.
- Redaction module (scrubs secrets/PII before persist).
- SQLite store with `0600` file permissions and parameterized SQL.
- `preflight --version` CLI entry point.
- CI (pytest + ruff) and `.gitignore` excluding secrets/DB/audit files.
