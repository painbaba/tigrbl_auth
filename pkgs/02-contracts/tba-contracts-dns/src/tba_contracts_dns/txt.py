from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class TxtStatus(str, Enum):
    FOUND = "found"
    ABSENT = "absent"
    TEMPORARY_FAILURE = "temporary_failure"


@dataclass(frozen=True, slots=True)
class TxtResult:
    status: TxtStatus
    records: tuple[bytes, ...] = ()


class TxtResolver(Protocol):
    def lookup_txt(self, name: str, /) -> TxtResult: ...
