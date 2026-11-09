from dataclasses import replace
from datetime import datetime, timezone

import cbor2
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from tba_protocol_ucan import (
    UcanDelegation,
    UcanError,
    UcanInvocation,
    UcanVerifier,
    content_id,
    did_key,
    sign_delegation,
    sign_invocation,
)
from tba_provider_replay_memory import MemoryReplayProvider

_COMMAND = "/documents/read"


@pytest.fixture
def chain():
    now = int(datetime.now(timezone.utc).timestamp())
    root_key = Ed25519PrivateKey.generate()
    alice_key = Ed25519PrivateKey.generate()
    worker_key = Ed25519PrivateKey.generate()
    root, alice, worker = (
        did_key(key.public_key()) for key in (root_key, alice_key, worker_key)
    )
    parent = UcanDelegation(
        root,
        alice,
        root,
        "/documents",
        (("==", ".project", "A"),),
        b"parent",
        now + 600,
    )
    child = UcanDelegation(
        alice,
        worker,
        root,
        _COMMAND,
        (("==", ".document_id", "42"),),
        b"child",
        now + 300,
    )
    parent_wire = sign_delegation(parent, root_key)
    child_wire = sign_delegation(child, alice_key)
    proofs = {content_id(wire): wire for wire in (parent_wire, child_wire)}
    revoked = set()
    verifier = UcanVerifier(
        resolve_proof=proofs.get,
        is_revoked=revoked.__contains__,
        replay=MemoryReplayProvider(),
    )
    call = UcanInvocation(
        worker,
        root,
        _COMMAND,
        {"project": "A", "document_id": "42"},
        b"",
        now + 120,
        tuple(proofs),
    )
    expected = {
        "expected_subject": root,
        "expected_executor": root,
        "expected_command": _COMMAND,
    }
    return verifier, call, worker_key, expected, proofs, revoked


@pytest.mark.asyncio
async def test_signed_documents_read_and_replay(chain):
    verifier, call, key, expected, _, _ = chain
    wire = sign_invocation(call, key)

    verified = await verifier.verify_invocation(wire, **expected)

    documents = {"42": "delegated document", "43": "private document"}
    assert verified.invocation.cmd == _COMMAND
    assert documents[verified.invocation.args["document_id"]] == "delegated document"
    assert verified.invocation.prf == call.prf
    assert verified.cid == content_id(wire)

    with pytest.raises(UcanError, match="replay"):
        await verifier.verify_invocation(wire, **expected)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "args",
    [{"project": "B", "document_id": "42"}, {"project": "A", "document_id": "43"}],
)
async def test_both_delegation_policies_apply_even_to_valid_signatures(chain, args):
    verifier, call, key, expected, _, _ = chain
    wire = sign_invocation(replace(call, args=args), key)
    with pytest.raises(UcanError, match="delegation policy"):
        await verifier.verify_invocation(wire, **expected)


@pytest.mark.asyncio
async def test_proof_substitution_is_rejected(chain):
    verifier, call, key, expected, proofs, _ = chain
    proofs[call.prf[0]] = proofs[call.prf[1]]
    with pytest.raises(UcanError, match="does not match its CID"):
        await verifier.verify_invocation(sign_invocation(call, key), **expected)


@pytest.mark.asyncio
async def test_revoked_parent_is_rejected(chain):
    verifier, call, key, expected, _, revoked = chain
    revoked.add(call.prf[0])
    with pytest.raises(UcanError, match="revoked"):
        await verifier.verify_invocation(sign_invocation(call, key), **expected)


@pytest.mark.asyncio
async def test_tampered_signed_arguments_are_rejected(chain):
    verifier, call, key, expected, _, _ = chain
    envelope = cbor2.loads(sign_invocation(call, key))
    envelope[1]["ucan/inv@1.0.0"]["args"]["document_id"] = "43"
    with pytest.raises(UcanError, match="signature"):
        await verifier.verify_invocation(
            cbor2.dumps(envelope, canonical=True), **expected
        )


@pytest.mark.asyncio
async def test_reordered_chain_is_rejected(chain):
    verifier, call, key, expected, _, _ = chain
    wire = sign_invocation(replace(call, prf=call.prf[::-1]), key)
    with pytest.raises(UcanError, match="broken delegation chain"):
        await verifier.verify_invocation(wire, **expected)


@pytest.mark.asyncio
async def test_wrong_executor_is_rejected(chain):
    verifier, call, key, expected, _, _ = chain
    with pytest.raises(UcanError, match="executor"):
        await verifier.verify_invocation(
            sign_invocation(call, key), **dict(expected, expected_executor=call.iss)
        )


@pytest.mark.asyncio
async def test_noncanonical_wire_is_rejected(chain):
    verifier, call, key, expected, _, _ = chain
    wire = sign_invocation(call, key)
    with pytest.raises(UcanError, match="noncanonical"):
        await verifier.verify_invocation(wire + b"\x00", **expected)
    with pytest.raises(UcanError, match="invalid DAG-CBOR"):
        await verifier.verify_invocation(wire[:1], **expected)
