# Changelog

All notable changes to Preflight are documented here.

## [Unreleased]

### Phase 0 — Scaffold & Schema
- Project packaging (`pyproject.toml`), uv-managed, pinned to Python 3.12.
- Core Pydantic v2 schemas: `Context`, `Action`, `Decision`, `Waste`.
- SHA-256 hash-chain primitive for the tamper-evident audit log.
- Redaction module (scrubs secrets/PII before persist).
- SQLite store with `0600` file permissions and parameterized SQL.
- `preflight --version` CLI entry point.
- CI (pytest + ruff) and `.gitignore` excluding secrets/DB/audit files.
