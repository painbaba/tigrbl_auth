"""Primitive claim taxonomy shared across token and credential families."""

from dataclasses import dataclass
from .enum_compat import StrEnum
from typing import TypeAlias


class ClaimType(StrEnum):
    IDENTITY = "identity"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    ASSURANCE = "assurance"
    CREDENTIAL = "credential"
    ATTESTATION = "attestation"
    SECURITY_EVENT = "security-event"
    WORKLOAD = "workload"
    TRANSACTION = "transaction"
    PROTOCOL = "protocol"


class ClaimValueType(StrEnum):
    STRING = "string"
    STRING_LIST = "string-list"
    NUMBER = "number"
    BOOLEAN = "boolean"
    URI = "uri"
    TIMESTAMP = "timestamp"
    JSON_OBJECT = "json-object"
    JSON_VALUE = "json-value"
    BYTES = "bytes"


class ClaimNameKind(StrEnum):
    """Registration form of a claim identifier, not its semantic purpose."""

    REGISTERED = "registered"
    SPECIFICATION = "specification"
    PROFILE = "profile"
    PRIVATE = "private"
    URI = "uri"
    INTEGER_LABEL = "integer-label"
    NAMESPACED = "namespaced"


class ClaimSourceKind(StrEnum):
    SUBJECT = "subject"
    SESSION = "session"
    CREDENTIAL = "credential"
    ATTESTATION = "attestation"
    DERIVED = "derived"
    PROVIDER = "provider"
    PRIVATE = "private"


class ClaimDisclosureMode(StrEnum):
    ALWAYS = "always"
    REQUESTED = "requested"
    CONSENTED = "consented"
    SELECTIVE = "selective"
    NEVER = "never"


ClaimLabel: TypeAlias = str | int


@dataclass(frozen=True, slots=True)
class ClaimIdentifier:
    """Carrier-neutral claim identifier.

    ``label`` supports both JSON string names and CWT/COSE integer labels.
    ``namespace`` covers mdoc namespaces and URI/profile qualified families.
    """

    label: ClaimLabel
    kind: ClaimNameKind = ClaimNameKind.SPECIFICATION
    namespace: str | None = None
    registry: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.label, bool) or not isinstance(self.label, (str, int)):
            raise TypeError("claim label must be a string or integer")
        if isinstance(self.label, str) and not self.label:
            raise ValueError("claim label must not be empty")
        if self.kind is ClaimNameKind.INTEGER_LABEL and not isinstance(self.label, int):
            raise ValueError("integer-label claims require an integer label")
        if self.kind is ClaimNameKind.NAMESPACED and not self.namespace:
            raise ValueError("namespaced claims require a namespace")


class RegisteredClaim(StrEnum):
    ISSUER = "iss"
    SUBJECT = "sub"
    AUDIENCE = "aud"
    EXPIRATION = "exp"
    NOT_BEFORE = "nbf"
    ISSUED_AT = "iat"
    JWT_ID = "jti"
    AUTH_TIME = "auth_time"
    NONCE = "nonce"
    AUTH_CONTEXT = "acr"
    AUTH_METHODS = "amr"
    AUTHORIZED_PARTY = "azp"
    CONFIRMATION = "cnf"
    SCOPE = "scope"
    CLIENT_ID = "client_id"
    VERIFIED_CLAIMS = "verified_claims"
    PLACE_OF_BIRTH = "place_of_birth"
    NATIONALITIES = "nationalities"
    BIRTH_FAMILY_NAME = "birth_family_name"
    BIRTH_GIVEN_NAME = "birth_given_name"
    BIRTH_MIDDLE_NAME = "birth_middle_name"
    SALUTATION = "salutation"
    TITLE = "title"
    MSISDN = "msisdn"
    ALSO_KNOWN_AS = "also_known_as"
    ADDRESS_COUNTRY_CODE = "address.country_code"
    CREDENTIAL_TYPE = "vct"
    CREDENTIAL_STATUS = "status"
    SECURITY_EVENTS = "events"
    TRANSACTION_ID = "txn"
    EAT_PROFILE = "eat_profile"


__all__ = [
    "ClaimDisclosureMode",
    "ClaimIdentifier",
    "ClaimLabel",
    "ClaimNameKind",
    "ClaimSourceKind",
    "ClaimType",
    "ClaimValueType",
    "RegisteredClaim",
]
