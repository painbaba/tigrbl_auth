from dataclasses import dataclass, field
from tba_primitives_identity.enum_compat import StrEnum
from typing import Mapping, Protocol, Sequence

from .entities import PolicyEntity


@dataclass(frozen=True, slots=True)
class PolicySearchRequest:
    subject: PolicyEntity
    action: str | None = None
    resource_type: str | None = None


@dataclass(frozen=True, slots=True)
class PolicySearchResult:
    entities: Sequence[PolicyEntity]
    cursor: str | None = None


class PolicySearchPort(Protocol):
    def search(self, request: PolicySearchRequest, /) -> PolicySearchResult: ...


class PolicyEntitySearchTarget(StrEnum):
    SUBJECT = "subject"
    RESOURCE = "resource"
    ACTION = "action"


@dataclass(frozen=True, slots=True)
class PolicyEntitySearchRequest:
    """Protocol-neutral search for entities permitted by a policy decision point."""

    target: PolicyEntitySearchTarget
    subject: PolicyEntity | None = None
    action: PolicyEntity | None = None
    resource: PolicyEntity | None = None
    context: Mapping[str, object] = field(default_factory=dict)
    page_token: str | None = None


@dataclass(frozen=True, slots=True)
class PolicyEntitySearchResult:
    entities: tuple[PolicyEntity, ...]
    next_page_token: str | None = None
    total: int | None = None
    context: Mapping[str, object] = field(default_factory=dict)


class PolicyEntitySearchPort(Protocol):
    def search_entities(
        self, request: PolicyEntitySearchRequest, /
    ) -> PolicyEntitySearchResult: ...


__all__ = [
    "PolicyEntitySearchPort",
    "PolicyEntitySearchRequest",
    "PolicyEntitySearchResult",
    "PolicyEntitySearchTarget",
    "PolicySearchPort",
    "PolicySearchRequest",
    "PolicySearchResult",
]
