from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from tba_protocol_zcap import (
    ZcapDelegation,
    ZcapError,
    ZcapRoot,
    ZcapVerifier,
    sign_delegation,
    sign_http_invocation,
)
from tba_provider_replay_memory import MemoryReplayProvider

_COLLECTION = "https://api.example/documents"
_DOCUMENT = _COLLECTION + "/42"


@pytest.fixture
def chain():
    now = datetime.now(timezone.utc).replace(microsecond=0)
    root = ZcapRoot("did:example:service", _COLLECTION)
    alice = ZcapDelegation(
        "urn:uuid:11111111-1111-4111-8111-111111111111",
        "did:example:alice",
        _COLLECTION,
        now + timedelta(hours=1),
        ("read",),
    )
    worker = ZcapDelegation(
        "urn:uuid:22222222-2222-4222-8222-222222222222",
        "did:example:worker",
        _DOCUMENT,
        now + timedelta(minutes=10),
        ("read",),
    )
    root_key, alice_key, worker_key = (Ed25519PrivateKey.generate() for _ in range(3))
    keys = {
        (
            root.controller,
            root.controller + "#key",
            "capabilityDelegation",
        ): root_key.public_key(),
        (
            alice.controller,
            alice.controller + "#key",
            "capabilityDelegation",
        ): alice_key.public_key(),
        (
            worker.controller,
            worker.controller + "#key",
            "capabilityInvocation",
        ): worker_key.public_key(),
        (
            root.controller,
            root.controller + "#key",
            "capabilityInvocation",
        ): root_key.public_key(),
    }
    parent = sign_delegation(
        alice,
        root,
        verification_method=root.controller + "#key",
        key=root_key,
        created=now,
    )
    revoked = set()
    roots = {root.id: root}
    verifier = ZcapVerifier(
        resolve_root=roots.get,
        resolve_key=lambda controller, method, purpose: keys.get(
            (controller, method, purpose)
        ),
        is_revoked=lambda root_id, cap_id: (root_id, cap_id) in revoked,
        replay=MemoryReplayProvider(),
    )

    def leaf(**changes):
        return sign_delegation(
            replace(worker, **changes),
            parent,
            verification_method=alice.controller + "#key",
            key=alice_key,
            created=now,
        )

    def request(capability=None, **changes):
        timestamp = int(now.timestamp())
        options = dict(
            method="GET",
            target=_DOCUMENT,
            action="read",
            key_id=worker.controller + "#key",
            key=worker_key,
            created=timestamp,
            expires=timestamp + 60,
            nonce="request-unique-001",
        )
        options.update(changes)
        return sign_http_invocation(
            leaf() if capability is None else capability, **options
        )

    expected = dict(
        expected_root=root.id,
        expected_method="GET",
        expected_target=_DOCUMENT,
        expected_action="read",
        now=now,
    )
    return (
        verifier,
        request,
        leaf,
        expected,
        roots,
        revoked,
        (root, alice, worker, root_key),
    )


@pytest.mark.asyncio
async def test_signed_document_read_and_replay(chain):
    verifier, request, _, expected, _, _, (_, alice, worker, _) = chain
    signed = request()
    verified = await verifier.verify_invocation(signed, **expected)
    assert verified.request.target == _DOCUMENT
    assert verified.action == "read"
    assert verified.controller == worker.controller
    assert verified.delegation_ids == (alice.id, worker.id)
    with pytest.raises(ZcapError, match="replay"):
        await verifier.verify_invocation(signed, **expected)


@pytest.mark.asyncio
async def test_direct_root_invocation(chain):
    verifier, request, _, expected, _, _, (root, _, _, key) = chain
    signed = request(root, key_id=root.controller + "#key", key=key)
    assert (await verifier.verify_invocation(signed, **expected)).delegation_ids == ()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("changes", "error"),
    [
        ({"target": _COLLECTION + "-other/42"}, "widens the invocation target"),
        ({"actions": ("read", "write")}, "widens the allowed actions"),
        ({"expires": datetime(2099, 1, 1, tzinfo=timezone.utc)}, "validity window"),
        ({"expires": datetime(2000, 1, 1, tzinfo=timezone.utc)}, "validity window"),
    ],
)
async def test_widened_or_expired_delegation_is_rejected(chain, changes, error):
    verifier, request, leaf, expected, *_ = chain
    with pytest.raises(ZcapError, match=error):
        await verifier.verify_invocation(request(leaf(**changes)), **expected)


@pytest.mark.asyncio
async def test_sibling_target_and_wrong_action_are_rejected(chain):
    verifier, request, _, expected, *_ = chain
    sibling = _COLLECTION + "/43"
    with pytest.raises(ZcapError, match="target is outside"):
        await verifier.verify_invocation(
            request(target=sibling), **dict(expected, expected_target=sibling)
        )
    with pytest.raises(ZcapError, match="action is outside"):
        await verifier.verify_invocation(
            request(action="write"), **dict(expected, expected_action="write")
        )


@pytest.mark.asyncio
async def test_tampered_delegation_and_wrong_key_are_rejected(chain):
    verifier, request, leaf, expected, _, _, (root, _, _, root_key) = chain
    tampered = leaf()
    tampered["expires"] = (
        (expected["now"] + timedelta(minutes=3)).isoformat().replace("+00:00", "Z")
    )
    with pytest.raises(ZcapError, match="invalid delegation signature"):
        await verifier.verify_invocation(request(tampered), **expected)
    with pytest.raises(ZcapError, match="key is not authorized"):
        await verifier.verify_invocation(
            request(key=root_key, key_id=root.controller + "#key"), **expected
        )


@pytest.mark.asyncio
async def test_revoked_parent_and_unknown_root_are_rejected(chain):
    verifier, request, _, expected, roots, revoked, (root, alice, _, _) = chain
    signed = request()
    revoked.add((root.id, alice.id))
    with pytest.raises(ZcapError, match="revoked"):
        await verifier.verify_invocation(signed, **expected)
    roots.clear()
    with pytest.raises(ZcapError, match="untrusted root"):
        await verifier.verify_invocation(signed, **expected)


@pytest.mark.asyncio
async def test_http_signature_binds_method_and_body(chain):
    verifier, request, _, expected, *_ = chain
    signed = request(body=b'{"id":42}', content_type="application/json")
    with pytest.raises(ZcapError, match="digest mismatch"):
        await verifier.verify_invocation(replace(signed, body=b'{"id":43}'), **expected)
    with pytest.raises(ZcapError, match="invalid HTTP invocation signature"):
        await verifier.verify_invocation(
            replace(signed, method="POST"), **dict(expected, expected_method="POST")
        )


@pytest.mark.asyncio
async def test_duplicate_protected_header_is_rejected(chain):
    verifier, request, _, expected, *_ = chain
    signed = request()
    headers = signed.headers + (
        ("Capability-Invocation", dict(signed.headers)["capability-invocation"]),
    )
    with pytest.raises(ZcapError, match="duplicate"):
        await verifier.verify_invocation(replace(signed, headers=headers), **expected)
