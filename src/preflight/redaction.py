"""Redaction pass — scrub secrets and PII BEFORE anything touches disk, logs,
exports, or the judge (CLAUDE.md §1, PRD S1).

Rules:
- Redact API keys, tokens, passwords, bearer/auth headers, private keys,
  credit-card/PAN numbers, SSNs, and emails (emails configurable).
- Redaction fails SAFE: if a value cannot be processed, the field is dropped,
  never stored raw.
- Where comparison across runs is needed, store a salted fingerprint, not the value.

This module is used everywhere from Phase 1 on. It must never be bypassed.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from typing import Any

REDACTED = "[REDACTED]"
DROPPED = "[DROPPED]"

# Key names whose values are always sensitive, regardless of content.
_SENSITIVE_KEY_TOKENS = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "access_key",
    "secret_key",
    "private_key",
    "authorization",
    "auth",
    "bearer",
    "credential",
    "session",
    "cookie",
)

# Value patterns. Order matters; first match wins per-string but we apply all.
_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Private key PEM blocks
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL),
    # Bearer / auth header values
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]+"),
    # OpenAI-style keys (sk-...), Anthropic (sk-ant-...), generic long secrets
    re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_\-]{16,}\b"),
    # AWS access key id
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    # GitHub tokens
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    # JWT (three base64url segments)
    re.compile(r"\beyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\b"),
    # Credit-card / PAN (13-19 digits, optional spaces/dashes)
    re.compile(r"\b(?:\d[ -]?){13,19}\b"),
    # US SSN
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    # Email
    re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
)


def _key_is_sensitive(key: str) -> bool:
    k = key.lower()
    return any(tok in k for tok in _SENSITIVE_KEY_TOKENS)


def redact_string(value: str) -> str:
    """Replace any matched secret/PII spans within a string with REDACTED."""
    out = value
    for pattern in _VALUE_PATTERNS:
        out = pattern.sub(REDACTED, out)
    return out


def redact_value(value: Any, *, _key: str | None = None) -> Any:
    """Recursively redact a value.

    Fails safe: any unexpected error while processing a field drops that field
    (returns DROPPED) rather than risking a raw secret leaking through.
    """
    try:
        if _key is not None and _key_is_sensitive(_key):
            return REDACTED
        if isinstance(value, str):
            return redact_string(value)
        if isinstance(value, dict):
            return {k: redact_value(v, _key=str(k)) for k, v in value.items()}
        if isinstance(value, list | tuple):
            return [redact_value(v) for v in value]
        if isinstance(value, int | float | bool) or value is None:
            return value
        # Unknown type: coerce to string and redact, so nothing exotic slips through raw.
        return redact_string(str(value))
    except Exception:
        # Fail safe — never store the raw value.
        return DROPPED


def redact(data: dict[str, Any]) -> dict[str, Any]:
    """Redact a dict (the common case: Context.inputs, Action.payload)."""
    result = redact_value(data)
    # redact_value on a dict returns a dict; guard the fail-safe path.
    if isinstance(result, dict):
        return result
    return {}


def fingerprint(value: str, salt: str) -> str:
    """Salted HMAC-SHA256 fingerprint for cross-run comparison without storing the value."""
    return hmac.new(salt.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()
