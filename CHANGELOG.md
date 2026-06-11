# Changelog

All notable changes to Preflight are documented here.

## [Unreleased]

### Phase 2 — Testing (golden set, replay, diff)
- Deterministic decision function (`decision.py`): pure function of frozen action +
  declarative policy — same input always yields the same verdict.
- Golden set (`golden.py`): freeze a known-good run; `preflight save <name>`.
- Deterministic replay (`replay.py`): re-derive decisions from a frozen golden;
  `preflight replay <name>`. Same golden + policy → byte-identical decisions.
- Side-by-side diff (`diff.py`) + regression detection (`regression.py`):
  `preflight diff <runA> <runB>` flags dangerous verdict relaxations on high-risk
  actions (block→allow, needs_approval→allow) and exits non-zero on regressions.
- Store extended with `goldens` / `replay_runs` tables.

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
