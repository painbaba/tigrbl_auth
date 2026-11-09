from tba_primitives_identity.enum_compat import StrEnum


class TokenProfile(StrEnum):
    ACCESS_TOKEN = "access-token"
    JWT_ACCESS_TOKEN = "jwt-access-token"
    ID_TOKEN = "id-token"
    REFRESH_TOKEN = "refresh-token"
    SECURITY_EVENT_TOKEN = "security-event-token"
    ENTITY_ATTESTATION_TOKEN = "entity-attestation-token"
    JWT_SVID = "jwt-svid"
    WIT = "wit"
    WIT_SVID = "wit-svid"
    WPT = "wpt"
    CWT_SVID_EXTENSION = "cwt-svid-extension"
    SD_JWT_KEY_BINDING = "kb-jwt"
    WALLET_ATTESTATION = "wallet-attestation"


class TokenEnvelopeFormat(StrEnum):
    JWT = "jwt"
    CWT = "cwt"


__all__ = ["TokenEnvelopeFormat", "TokenProfile"]
