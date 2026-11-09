"""Models and strict input rules for the ZCAP-LD HTTP profile."""

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

from .versions import CRYPTOSUITE, DATA_INTEGRITY_CONTEXT, ZCAP_CONTEXT

_TARGET = re.compile(r"https://[a-z0-9-]+(?:\.[a-z0-9-]+)*(?:/[A-Za-z0-9_.~-]+)+")
_URI = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*:[A-Za-z0-9._~:/?#@!$&'()*+,;=%-]+")
ACTION = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,63}")
_CONTEXTS = (ZCAP_CONTEXT, DATA_INTEGRITY_CONTEXT)


class ZcapError(ValueError):
    """Malformed or unauthorized ZCAP-LD input."""


def validate_uri(value: object) -> None:
    if not isinstance(value, str) or len(value) > 2048 or not _URI.fullmatch(value):
        raise ZcapError("expected an absolute URI")


def validate_target(value: object) -> None:
    if (
        not isinstance(value, str)
        or len(value) > 1024
        or not _TARGET.fullmatch(value)
        or any(segment in {".", ".."} for segment in value.split("/"))
    ):
        raise ZcapError("expected a canonical HTTPS target with a simple path")


def covers_target(parent: str, child: str) -> bool:
    return child == parent or child.startswith(parent + "/")


def parse_time(value: object) -> datetime:
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", value
    ):
        raise ZcapError("expected a UTC timestamp with second precision")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ZcapError("invalid capability timestamp") from exc


def format_time(value: datetime) -> str:
    if value.utcoffset() is None or value.microsecond:
        raise ZcapError("expected a timezone-aware timestamp with second precision")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class ZcapRoot:
    controller: str
    target: str

    def __post_init__(self) -> None:
        validate_uri(self.controller)
        validate_target(self.target)

    @property
    def id(self) -> str:
        return "urn:zcap:root:" + quote(self.target, safe="")

    def to_document(self) -> dict[str, str]:
        return {
            "@context": ZCAP_CONTEXT,
            "id": self.id,
            "controller": self.controller,
            "invocationTarget": self.target,
        }


@dataclass(frozen=True, slots=True)
class ZcapDelegation:
    id: str
    controller: str
    target: str
    expires: datetime
    actions: tuple[str, ...]

    def to_document(self, parent_id: str) -> dict[str, Any]:
        document = {
            "@context": list(_CONTEXTS),
            "id": self.id,
            "controller": self.controller,
            "invocationTarget": self.target,
            "parentCapability": parent_id,
            "expires": format_time(self.expires),
            "allowedAction": list(self.actions),
        }
        parse_delegation(document)
        return document


def parse_delegation(document: dict[str, Any]) -> ZcapDelegation:
    fields = {
        "@context",
        "id",
        "controller",
        "invocationTarget",
        "parentCapability",
        "expires",
        "allowedAction",
    }
    if set(document) - {"proof"} != fields or document["@context"] != list(_CONTEXTS):
        raise ZcapError("unexpected delegated capability fields or contexts")
    for key in ("id", "controller", "parentCapability"):
        validate_uri(document[key])
    if document["id"].startswith("urn:zcap:root:"):
        raise ZcapError("a delegation cannot use a root capability ID")
    validate_target(document["invocationTarget"])
    actions = document["allowedAction"]
    if isinstance(actions, str):
        actions = [actions]
    if (
        not isinstance(actions, list)
        or not actions
        or any(
            not isinstance(action, str) or not ACTION.fullmatch(action)
            for action in actions
        )
        or len(set(actions)) != len(actions)
    ):
        raise ZcapError("expected explicit, distinct capability actions")
    return ZcapDelegation(
        document["id"],
        document["controller"],
        document["invocationTarget"],
        parse_time(document["expires"]),
        tuple(actions),
    )


def delegation_proof(document: dict[str, Any]) -> dict[str, Any]:
    proof = document.get("proof")
    required = {
        "type",
        "cryptosuite",
        "proofPurpose",
        "created",
        "verificationMethod",
        "capabilityChain",
        "proofValue",
    }
    if (
        not isinstance(proof, dict)
        or set(proof) - {"@context"} != required
        or proof["type"] != "DataIntegrityProof"
        or proof["cryptosuite"] != CRYPTOSUITE
        or proof["proofPurpose"] != "capabilityDelegation"
        or ("@context" in proof and proof["@context"] != document.get("@context"))
    ):
        raise ZcapError("unexpected capability delegation proof")
    validate_uri(proof["verificationMethod"])
    parse_time(proof["created"])
    return proof


@dataclass(frozen=True, slots=True)
class ZcapHttpInvocation:
    method: str
    target: str
    headers: tuple[tuple[str, str], ...]
    body: bytes = b""
