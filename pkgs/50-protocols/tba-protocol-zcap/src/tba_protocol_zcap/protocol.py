"""Verify ZCAP-LD chains and bind them to one signed HTTP request."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from tba_contracts_replay import (
    ReplayKey,
    ReplayReservationPort,
    ReplayReservationRequest,
)
from tba_codec_jcs import canonicalize

from .http import read_invocation_signature
from .proofs import embedded_chain, verify_delegation_signature
from .schemas import (
    ZcapError,
    ZcapHttpInvocation,
    ZcapRoot,
    covers_target,
    delegation_proof,
    parse_delegation,
    parse_time,
)
from .versions import PROFILE

_MAX_SIGNATURE_AGE = 300
_MAX_CLOCK_SKEW = 30
_MAX_DELEGATION_TTL = timedelta(days=90)


@dataclass(frozen=True, slots=True)
class VerifiedZcapInvocation:
    root_id: str
    delegation_ids: tuple[str, ...]
    controller: str
    verification_method: str
    action: str
    request: ZcapHttpInvocation
    expires_at: datetime
    profile: str = PROFILE


class ZcapVerifier:
    """Use local trust, purpose-aware key resolution, and atomic replay storage."""

    def __init__(
        self,
        *,
        resolve_root: Callable[[str], ZcapRoot | None],
        resolve_key: Callable[[str, str, str], Ed25519PublicKey | None],
        is_revoked: Callable[[str, str], bool],
        replay: ReplayReservationPort,
    ) -> None:
        self._resolve_root = resolve_root
        self._resolve_key = resolve_key
        self._is_revoked = is_revoked
        self._replay = replay

    def _key(self, controller: str, method: str, purpose: str) -> Ed25519PublicKey:
        key = self._resolve_key(controller, method, purpose)
        if not isinstance(key, Ed25519PublicKey):
            raise ZcapError(f"key is not authorized for {purpose}")
        return key

    async def verify_invocation(
        self,
        request: ZcapHttpInvocation,
        *,
        expected_root: str,
        expected_method: str,
        expected_target: str,
        expected_action: str,
        now: datetime | None = None,
    ) -> VerifiedZcapInvocation:
        now = datetime.now(timezone.utc) if now is None else now
        if now.utcoffset() is None:
            raise ZcapError("verification time must include a timezone")
        if (request.method, request.target) != (expected_method, expected_target):
            raise ZcapError("unexpected HTTP method or target")
        invocation = read_invocation_signature(request)
        if invocation.action != expected_action:
            raise ZcapError("unexpected capability action")
        timestamp = now.timestamp()
        if (
            not 0 < invocation.expires - invocation.created <= _MAX_SIGNATURE_AGE
            or invocation.created > timestamp + _MAX_CLOCK_SKEW
            or invocation.expires <= timestamp
        ):
            raise ZcapError("HTTP signature is outside its validity window")
        expires = datetime.fromtimestamp(invocation.expires, timezone.utc)

        if isinstance(invocation.capability, str):
            root_id, documents = invocation.capability, []
        else:
            root_id, documents = embedded_chain(invocation.capability)
        if root_id != expected_root:
            raise ZcapError("unexpected root capability")
        root = self._resolve_root(root_id)
        if not isinstance(root, ZcapRoot) or root.id != root_id:
            raise ZcapError("untrusted root capability")

        controller, target = root.controller, root.target
        parent_expiry, parent_created, actions = None, None, None
        delegation_ids = []
        for document in documents:
            delegation = parse_delegation(document)
            proof = delegation_proof(document)
            created = parse_time(proof["created"])
            if self._is_revoked(root_id, delegation.id):
                raise ZcapError("delegated capability is revoked")
            if not covers_target(target, delegation.target):
                raise ZcapError("delegation widens the invocation target")
            if actions is not None and not set(delegation.actions).issubset(actions):
                raise ZcapError("delegation widens the allowed actions")
            if (
                delegation.expires <= now
                or not timedelta(0)
                < delegation.expires - created
                <= _MAX_DELEGATION_TTL
                or created.timestamp() > invocation.created
                or (parent_created is not None and created < parent_created)
                or (parent_expiry is not None and delegation.expires > parent_expiry)
            ):
                raise ZcapError("invalid or widened delegation validity window")
            key = self._key(
                controller, proof["verificationMethod"], "capabilityDelegation"
            )
            verify_delegation_signature(document, key)
            controller, target, actions = (
                delegation.controller,
                delegation.target,
                delegation.actions,
            )
            parent_expiry, parent_created = delegation.expires, created
            delegation_ids.append(delegation.id)

        if not covers_target(target, request.target):
            raise ZcapError("request target is outside the capability")
        if actions is not None and invocation.action not in actions:
            raise ZcapError("request action is outside the capability")
        key = self._key(controller, invocation.key_id, "capabilityInvocation")
        try:
            key.verify(invocation.signature, invocation.signing_input)
        except InvalidSignature as exc:
            raise ZcapError("invalid HTTP invocation signature") from exc

        nonce_key = sha256(
            canonicalize([invocation.key_id, invocation.nonce])
        ).hexdigest()
        reservation = await self._replay.check_and_reserve(
            ReplayReservationRequest(ReplayKey(PROFILE, nonce_key), expires)
        )
        if not reservation.accepted:
            raise ZcapError("HTTP invocation replay reservation rejected")
        return VerifiedZcapInvocation(
            root_id,
            tuple(delegation_ids),
            controller,
            invocation.key_id,
            invocation.action,
            request,
            min(parent_expiry, expires) if parent_expiry else expires,
        )
