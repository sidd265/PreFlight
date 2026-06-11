"""Phase 0: redaction strips known secret patterns and fails safe."""

from __future__ import annotations

import json

from preflight.redaction import DROPPED, REDACTED, fingerprint, redact, redact_string


def test_redacts_openai_style_key():
    out = redact_string("here is sk-ant-1234567890abcdefghij my key")
    assert "sk-ant-1234567890abcdefghij" not in out
    assert REDACTED in out


def test_redacts_sensitive_key_names():
    out = redact({"password": "hunter2", "api_key": "anything", "note": "ok"})
    assert out["password"] == REDACTED
    assert out["api_key"] == REDACTED
    assert out["note"] == "ok"


def test_redacts_nested_structures():
    data = {"outer": {"authorization": "Bearer abc.def.ghi", "list": ["sk-ant-abcdefghijklmnop1"]}}
    out = redact(data)
    blob = json.dumps(out)
    assert "abc.def.ghi" not in blob
    assert "sk-ant-abcdefghijklmnop1" not in blob


def test_redacts_email_and_ssn_and_pan():
    out = redact(
        {
            "email": "a@b.com",  # key name not sensitive, value pattern catches it
            "ssn": "123-45-6789",
            "card": "4111 1111 1111 1111",
        }
    )
    blob = json.dumps(out)
    assert "a@b.com" not in blob
    assert "123-45-6789" not in blob
    assert "4111" not in blob


def test_redaction_fails_safe_on_bad_object():
    class Boom:
        def __str__(self):
            raise RuntimeError("nope")

    out = redact({"weird": Boom()})
    assert out["weird"] == DROPPED


def test_known_secret_never_appears_raw():
    secret = "sk-ant-PLANTEDSECRET0123456789"
    out = redact({"context": {"prompt": f"call with {secret}", "creds": {"token": secret}}})
    assert secret not in json.dumps(out)


def test_fingerprint_is_stable_and_salted():
    a = fingerprint("value", "salt1")
    b = fingerprint("value", "salt1")
    c = fingerprint("value", "salt2")
    assert a == b
    assert a != c
    assert "value" not in a
