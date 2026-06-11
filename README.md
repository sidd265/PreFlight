# Preflight (`cc-preflight`)

> Preflight watches your AI agents, catches the moment one is about to do something expensive or
> wrong, proves the decision was right, keeps the receipts — and tells you how much of your agents'
> work is real versus wasted.

Preflight is a **local-only, security-and-audit CLI** for AI agents. It runs entirely on your
machine — no account, no cloud, no data egress (the only outbound call is an optional, user-configured
LLM judge with your own key).

## Status

Early development. Building the free CLI in phases (0–5). Done: **Phase 0 — Scaffold &
Schema**, **Phase 1 — Recording + Waste Report**, **Phase 2 — Testing (golden set,
replay, diff)**, **Phase 3 — Checking (judge, approval, dry-run)**.

### Live judge demo (optional, BYO key)

```bash
uv sync --extra judge

# Anthropic (default)
$env:ANTHROPIC_API_KEY = "sk-ant-..."   # your own key; never shipped
uv run preflight demo --live --html judge_demo.html

# or Gemini
$env:GEMINI_API_KEY = "..."
uv run preflight demo --live --provider gemini --html judge_demo.html
```

Without `--live` the command refuses to make any network call, so CI never touches it.

### Try it

```bash
uv sync --extra dev
# record the sample agent into a local DB, then report on it:
uv run python -c "from preflight.store import Store; from examples.sample_agent import run_sample_agent; s=Store('.preflight/preflight.db'); run_sample_agent(s); s.close()"
uv run preflight report
uv run preflight report --html report.html
```

## Install (development)

```bash
uv sync --extra dev      # create the env and install pinned deps
uv run preflight --version
```

## Commands (target UX)

```
preflight report                 # waste & ROI report (real vs wasted, $ spent, $ wasted)
preflight save <name>            # snapshot a situation into the golden set
preflight replay <name>          # deterministic re-run from frozen context
preflight diff <runA> <runB>     # side-by-side, with danger flags
preflight verify                 # check audit-log integrity (tamper detection)
preflight export --format md|html|json --out <dir>
```

## Security

This is a security product. Secrets and PII are **redacted before anything touches disk**, guards
**fail closed**, and the audit log is **append-only and tamper-evident** (SHA-256 hash chain). See
`CLAUDE.md` for the full, non-negotiable security rules.

## License

Apache-2.0 (free core).
