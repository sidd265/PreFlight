"""Phase 0: hash-chain links correctly."""

from __future__ import annotations

from preflight.hashchain import (
    GENESIS_PREV_HASH,
    compute_record_hashes,
    content_hash,
    link_hash,
)


def test_genesis_is_64_zeros():
    assert GENESIS_PREV_HASH == "0" * 64
    assert len(GENESIS_PREV_HASH) == 64


def test_content_hash_is_order_independent():
    a = content_hash({"x": 1, "y": 2})
    b = content_hash({"y": 2, "x": 1})
    assert a == b


def test_content_hash_changes_with_content():
    assert content_hash({"x": 1}) != content_hash({"x": 2})


def test_link_hash_is_sha256_of_concat():
    import hashlib

    expected = hashlib.sha256((GENESIS_PREV_HASH + "deadbeef").encode()).hexdigest()
    assert link_hash(GENESIS_PREV_HASH, "deadbeef") == expected


def test_chain_links_record_to_predecessor():
    rec1 = {"action": "a"}
    ch1, h1 = compute_record_hashes(rec1, GENESIS_PREV_HASH)
    assert ch1 == content_hash(rec1)
    assert h1 == link_hash(GENESIS_PREV_HASH, ch1)

    rec2 = {"action": "b"}
    ch2, h2 = compute_record_hashes(rec2, h1)
    # Second record's hash depends on the first record's hash → chained.
    assert h2 == link_hash(h1, ch2)
    assert h2 != link_hash(GENESIS_PREV_HASH, ch2)


def test_tampering_breaks_link():
    rec = {"amount": 5000}
    ch, h = compute_record_hashes(rec, GENESIS_PREV_HASH)
    tampered = {"amount": 9999}
    ch_t, _ = compute_record_hashes(tampered, GENESIS_PREV_HASH)
    assert ch != ch_t
