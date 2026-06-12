# Changelog

All notable changes to Preflight are documented here.

## [Unreleased]

### Phase 5 — Proving (audit verify + export)
- `verify.py`: recomputes the SHA-256 hash chain and detects **any** tampering —
  content alteration, insertion, reorder, or deletion (S4). Read-only; reports the
  first bad record. `preflight verify` exits non-zero on tamper.
- `export.py`: exports the audit trail to **JSON / Markdown / HTML**, including each
  record's hashes so the trail can be re-verified. Output is **path-confined** to the
  working directory (no traversal, S7). `preflight export --out <dir> --format ...`.
- `preflight guard` now appends each decision to the append-only audit chain, so a
  guarded run produces a tamper-evident trail to verify and export.

### Phase 4 — Guarding (spend limits, policy)
- Spend guard (`guard.py`): per-run **budget** checked BEFORE each action; a breach
  trips a latching **kill switch** so every later action is blocked.
- Declarative **policy-as-code**: `GuardPolicy`/`PolicyRule` are pure Pydantic data,
  loaded from `preflight.yaml` with `yaml.safe_load` — no `eval`/`exec`/`pickle` (S7).
  First matching rule wins (allow / block / needs_approval).
- Guards **fail CLOSED** (S3): any error in budget or policy evaluation — including a
  corrupt cost or a broken rule — yields `block`, never `allow`.
- `preflight guard --policy preflight.yaml`: replays a recorded run through the guard,
  prints each verdict, totals spend vs budget, exits non-zero if anything was blocked.
- Sample policy at `examples/preflight.yaml`; `pyyaml` added (declarative config only).

### Phase 3 — Checking (judge, approval, dry-run)
- LLM judge (`judge.py`): provider-agnostic `JudgeClient`, BYO key, small-model
  default. Context scrubbed before sending; recorded content wrapped as untrusted
  data; system prompt hardened against prompt injection (S5). Fails CLOSED — any
  client error or unparseable output yields `block`, never auto-allow (S3).
- Human approval gate (`approval.py`): pauses for `needs_approval` actions and
  default-denies anything but an explicit yes.
- Dry-run (`dryrun.py`): structurally incapable of a real side effect (S6) — the
  dry-run branch never references the executor.
- `preflight demo` (opt-in `--live`): runs the real judge against a risky and an
  injection scenario, prints verdicts, writes an HTML report. Never called by CI;
  requires the optional `judge` extra and the provider's API key.
  - `--provider anthropic` (default, `ANTHROPIC_API_KEY`) or `--provider gemini`
    (`GEMINI_API_KEY`). Both keep recorded content separate from the hardened system
    instructions.

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
