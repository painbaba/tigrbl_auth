from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol


class DomainOutcome(str, Enum):
    READY = "ready"
    NOT_READY = "not_ready"
    INDETERMINATE = "indeterminate"


@dataclass(frozen=True, slots=True)
class DomainCheck:
    domain: str
    outcome: DomainOutcome
    details: Mapping[str, str | None] = field(default_factory=dict)


class DomainChecker(Protocol):
    @property
    def profile(self) -> str: ...

    def check(self, domain: str, /) -> DomainCheck: ...


class AuditWriter(Protocol):
    async def __call__(self, *, db: object, **payload: object) -> object: ...
