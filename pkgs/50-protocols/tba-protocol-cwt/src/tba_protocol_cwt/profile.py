from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True, slots=True)
class CwtProfile:
    name: str
    required_claim_labels: frozenset[str | int]
    allowed_cose_message_types: frozenset[str]

    def validate(self, claims: Mapping[str | int, object], cose_message_type: str) -> None:
        if cose_message_type not in self.allowed_cose_message_types:
            raise ValueError(
                f"COSE message type not allowed by {self.name}: {cose_message_type}"
            )
        missing = self.required_claim_labels.difference(claims)
        if missing:
            raise ValueError(f"missing required CWT claim labels: {sorted(missing, key=str)}")
