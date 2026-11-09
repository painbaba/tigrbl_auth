"""ZCAP delegation proofs using the W3C eddsa-jcs-2022 suite."""

from datetime import datetime
from hashlib import sha256
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from tba_codec_multibase import decode_base58btc, encode_base58btc
from tba_codec_jcs import canonicalize

from .schemas import (
    ZcapDelegation,
    ZcapError,
    ZcapRoot,
    delegation_proof,
    format_time,
    validate_uri,
)
from .versions import CRYPTOSUITE

_MAX_DELEGATIONS = 8


def _signature(value: object) -> bytes:
    if not isinstance(value, str) or not value.startswith("z") or len(value) > 89:
        raise ZcapError("expected a base58btc delegation signature")
    try:
        signature = decode_base58btc(value)
    except ValueError as exc:
        raise ZcapError("invalid delegation signature encoding") from exc
    if len(signature) != 64:
        raise ZcapError("invalid delegation signature encoding")
    return signature


def _signing_input(document: dict, proof: dict) -> bytes:
    unsecured = {key: value for key, value in document.items() if key != "proof"}
    options = {key: value for key, value in proof.items() if key != "proofValue"}
    try:
        return (
            sha256(canonicalize(options)).digest()
            + sha256(canonicalize(unsecured)).digest()
        )
    except (ValueError, RecursionError) as exc:
        raise ZcapError("cannot canonicalize capability delegation") from exc


def embedded_chain(leaf: dict) -> tuple[str, list[dict]]:
    """Collect embedded delegations in root-to-leaf order and check references."""
    backwards = []
    document = leaf
    while True:
        if len(backwards) >= _MAX_DELEGATIONS:
            raise ZcapError("capability chain exceeds the profile limit")
        chain = delegation_proof(document)["capabilityChain"]
        if not isinstance(chain, list) or not 1 <= len(chain) <= _MAX_DELEGATIONS:
            raise ZcapError("invalid capability chain")
        backwards.append(document)
        if len(chain) == 1:
            root_id = chain[0]
            validate_uri(root_id)
            break
        if not isinstance(chain[-1], dict):
            raise ZcapError("parent delegation must be embedded")
        document = chain[-1]

    documents = list(reversed(backwards))
    ids = [root_id]
    for document in documents:
        chain = document["proof"]["capabilityChain"]
        # The immediate parent is embedded, and older ancestors are references.
        references = chain if len(ids) == 1 else chain[:-1] + [chain[-1].get("id")]
        if references != ids or document.get("parentCapability") != ids[-1]:
            raise ZcapError("capability chain ancestry does not match parent links")
        capability_id = document.get("id")
        validate_uri(capability_id)
        if capability_id in ids:
            raise ZcapError("repeated capability ID")
        ids.append(capability_id)
    return root_id, documents


def sign_delegation(
    delegation: ZcapDelegation,
    parent: ZcapRoot | dict[str, Any],
    *,
    verification_method: str,
    key: Ed25519PrivateKey,
    created: datetime,
) -> dict[str, Any]:
    validate_uri(verification_method)
    if isinstance(parent, ZcapRoot):
        parent_id = parent.id
        chain = [parent_id]
    else:
        root_id, ancestors = embedded_chain(parent)
        if len(ancestors) >= _MAX_DELEGATIONS:
            raise ZcapError("capability chain exceeds the profile limit")
        parent_id = parent["id"]
        chain = [root_id, *(doc["id"] for doc in ancestors[:-1]), parent]
    document = delegation.to_document(parent_id)
    proof = {
        "@context": document["@context"].copy(),
        "type": "DataIntegrityProof",
        "cryptosuite": CRYPTOSUITE,
        "proofPurpose": "capabilityDelegation",
        "created": format_time(created),
        "verificationMethod": verification_method,
        "capabilityChain": chain,
    }
    proof["proofValue"] = encode_base58btc(key.sign(_signing_input(document, proof)))
    return {**document, "proof": proof}


def verify_delegation_signature(document: dict, key: Ed25519PublicKey) -> None:
    proof = delegation_proof(document)
    try:
        key.verify(_signature(proof["proofValue"]), _signing_input(document, proof))
    except InvalidSignature as exc:
        raise ZcapError("invalid delegation signature") from exc
