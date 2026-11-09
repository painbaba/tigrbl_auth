"""UCAN signing and delegated invocation verification."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from tba_contracts_replay import (
    ReplayKey,
    ReplayReservationPort,
    ReplayReservationRequest,
)

from .codec import UcanEnvelopeCodec, UcanError, content_id
from .policy import covers_command, enforce_policy
from .schemas import UcanDelegation, UcanInvocation
from .versions import DELEGATION_TAG, INVOCATION_TAG, PROFILE

_MAX_INVOCATION_LIFETIME = 300


def sign_delegation(delegation: UcanDelegation, key: Ed25519PrivateKey) -> bytes:
    return UcanEnvelopeCodec().sign(DELEGATION_TAG, delegation.to_payload(), key)


def sign_invocation(invocation: UcanInvocation, key: Ed25519PrivateKey) -> bytes:
    return UcanEnvelopeCodec().sign(INVOCATION_TAG, invocation.to_payload(), key)


@dataclass(frozen=True, slots=True)
class VerifiedUcanInvocation:
    invocation: UcanInvocation
    cid: str
    profile: str = PROFILE


class UcanVerifier:
    """Verify a closed delegation chain and reserve the invocation before execution."""

    def __init__(
        self,
        *,
        resolve_proof: Callable[[str], bytes | None],
        is_revoked: Callable[[str], bool],
        replay: ReplayReservationPort,
    ) -> None:
        self._resolve_proof = resolve_proof
        self._is_revoked = is_revoked
        self._replay = replay
        self._codec = UcanEnvelopeCodec()

    async def verify_invocation(
        self,
        wire: bytes,
        *,
        expected_subject: str,
        expected_executor: str,
        expected_command: str,
        now: datetime | None = None,
    ) -> VerifiedUcanInvocation:
        now = datetime.now(timezone.utc) if now is None else now
        if now.utcoffset() is None:
            raise UcanError("verification time must include a timezone")
        timestamp = now.timestamp()
        invocation = UcanInvocation.from_payload(
            self._codec.verify(wire, INVOCATION_TAG)
        )
        if (
            invocation.sub != expected_subject
            or invocation.executor != expected_executor
        ):
            raise UcanError("unexpected invocation subject or executor")
        if invocation.cmd != expected_command:
            raise UcanError("unexpected invocation command")
        if not timestamp < invocation.exp <= timestamp + _MAX_INVOCATION_LIFETIME:
            raise UcanError("invocation expired or exceeds the allowed lifetime")
        self._verify_chain(invocation, timestamp)
        cid = content_id(wire)
        reservation = await self._replay.check_and_reserve(
            ReplayReservationRequest(
                ReplayKey(PROFILE, cid),
                datetime.fromtimestamp(invocation.exp, timezone.utc),
            )
        )
        if not reservation.accepted:
            raise UcanError("invocation replay reservation rejected")
        return VerifiedUcanInvocation(invocation, cid)

    def _verify_chain(self, invocation: UcanInvocation, now: float) -> None:
        next_issuer = invocation.sub
        parent_command = "/"
        for cid in invocation.prf:
            wire = self._resolve_proof(cid)
            if wire is None:
                raise UcanError("missing delegation proof")
            delegation = UcanDelegation.from_payload(
                self._codec.verify(wire, DELEGATION_TAG)
            )
            if content_id(wire) != cid:
                raise UcanError("resolved proof does not match its CID")
            if self._is_revoked(cid):
                raise UcanError("delegation is revoked")
            if delegation.iss != next_issuer or delegation.sub != invocation.sub:
                raise UcanError("broken delegation chain")
            if delegation.exp <= now or (
                delegation.nbf is not None and delegation.nbf > now
            ):
                raise UcanError("delegation is outside its validity window")
            if not covers_command(parent_command, delegation.cmd):
                raise UcanError("delegation widens the command path")
            if not covers_command(delegation.cmd, invocation.cmd):
                raise UcanError("invocation command is outside the delegation")
            enforce_policy(delegation.pol, invocation.args)
            next_issuer, parent_command = delegation.aud, delegation.cmd
        if next_issuer != invocation.iss:
            raise UcanError("delegation chain does not reach the invoker")
