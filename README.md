# Preflight (`cc-preflight`)

> Preflight watches your AI agents, catches the moment one is about to do something expensive or
> wrong, proves the decision was right, keeps the receipts — and tells you how much of your agents'
> work is real versus wasted.

Preflight is a **local-only, security-and-audit CLI** for AI agents. It runs entirely on your
machine — no account, no cloud, no data egress (the only outbound call is an optional, user-configured
LLM judge with your own key).

## Status

Early development. Building the free CLI in phases (0–5). Currently: **Phase 0 — Scaffold & Schema**.

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
