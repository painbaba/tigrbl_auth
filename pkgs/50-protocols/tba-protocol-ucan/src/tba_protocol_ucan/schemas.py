"""Typed payloads for the supported UCAN wire profile."""

from dataclasses import dataclass
from typing import Any

from .codec import UcanError, cid_link, link_cid, validate_did
from .policy import validate_command, validate_policy

_MAX_CHAIN = 16
_MAX_TIMESTAMP = 2**53 - 1


def _timestamp(value: object) -> None:
    if type(value) is not int or not 0 <= value <= _MAX_TIMESTAMP:
        raise UcanError("profile requires a finite Unix timestamp")


def _fields(payload: dict, required: set[str], optional: set[str]) -> None:
    if required - payload.keys() or payload.keys() - required - optional:
        raise UcanError("unexpected UCAN payload fields")


@dataclass(frozen=True, slots=True)
class UcanDelegation:
    iss: str
    aud: str
    sub: str
    cmd: str
    pol: tuple[tuple[str, str, Any], ...]
    nonce: bytes
    exp: int
    nbf: int | None = None

    @classmethod
    def from_payload(cls, payload: dict) -> "UcanDelegation":
        _fields(payload, {"iss", "aud", "sub", "cmd", "pol", "nonce", "exp"}, {"nbf"})
        for key in ("iss", "aud", "sub"):
            validate_did(payload[key])
        validate_command(payload["cmd"])
        _timestamp(payload["exp"])
        if "nbf" in payload:
            _timestamp(payload["nbf"])
            if payload["nbf"] >= payload["exp"]:
                raise UcanError("invalid delegation time window")
        if type(payload["nonce"]) is not bytes or type(payload["pol"]) is not list:
            raise UcanError("invalid delegation nonce or policy")
        validate_policy(tuple(payload["pol"]))
        values = dict(payload)
        values["pol"] = tuple(tuple(predicate) for predicate in payload["pol"])
        return cls(**values)

    def to_payload(self) -> dict:
        payload = {
            "iss": self.iss,
            "aud": self.aud,
            "sub": self.sub,
            "cmd": self.cmd,
            "pol": list(self.pol),
            "nonce": self.nonce,
            "exp": self.exp,
        }
        if self.nbf is not None:
            payload["nbf"] = self.nbf
        self.from_payload(payload)
        return payload


@dataclass(frozen=True, slots=True)
class UcanInvocation:
    iss: str
    sub: str
    cmd: str
    args: dict[str, Any]
    nonce: bytes
    exp: int
    prf: tuple[str, ...]
    aud: str | None = None

    @property
    def executor(self) -> str:
        return self.sub if self.aud is None else self.aud

    @classmethod
    def from_payload(cls, payload: dict) -> "UcanInvocation":
        _fields(payload, {"iss", "sub", "cmd", "args", "nonce", "exp", "prf"}, {"aud"})
        validate_did(payload["iss"])
        validate_did(payload["sub"])
        if "aud" in payload:
            validate_did(payload["aud"])
            if payload["aud"] == payload["sub"]:
                raise UcanError("omit audience when the subject is the executor")
        validate_command(payload["cmd"])
        _timestamp(payload["exp"])
        if type(payload["args"]) is not dict or type(payload["nonce"]) is not bytes:
            raise UcanError("invalid invocation arguments or nonce")
        links = payload["prf"]
        if type(links) is not list or not 1 <= len(links) <= _MAX_CHAIN:
            raise UcanError("expected a bounded nonempty delegation chain")
        values = dict(payload)
        values["prf"] = tuple(link_cid(link) for link in links)
        if len(set(values["prf"])) != len(links):
            raise UcanError("duplicate delegation proof")
        return cls(**values)

    def to_payload(self) -> dict:
        payload = {
            "iss": self.iss,
            "sub": self.sub,
            "cmd": self.cmd,
            "args": self.args,
            "nonce": self.nonce,
            "exp": self.exp,
            "prf": [cid_link(cid) for cid in self.prf],
        }
        if self.aud is not None:
            payload["aud"] = self.aud
        self.from_payload(payload)
        return payload
