"""Versioned CBOR Web Token protocol ownership."""

from tba_contracts_identity.protocol_processing import (
    build_protocol_capability_report,
)

from .bindings import CAPABILITY_REQUIREMENTS
from .claims import (
    CWT_CLAIM_BY_LABEL,
    CWT_EXTENSION_CLAIMS,
    build_cwt_claims,
    CWT_LABEL_BY_CLAIM,
    CWT_REGISTERED_CLAIMS,
    CwtClaimBinding,
    compose_cwt_claim_set,
    cwt_label_for,
)
from .compatibility import COMPATIBILITY_PATHS, CwtCompatibility, compatibility
from .errors import CwtProtocolError, UnsupportedCwtMediaTypeError
from .features import FEATURES_BY_VERSION, supports
from .migrations import migrate_claims
from .profile import CwtProfile
from .protocol import CwtProtocol
from .schemas import CWT_CARRIER, CwtCarrier, select_carrier
from .versions import (
    CURRENT_VERSION,
    VERSION_HISTORY,
    VERSION_PUBLISHED,
    VERSION_STATUS,
    CwtVersion,
    select_version,
)


def capability_report() -> dict[str, object]:
    return build_protocol_capability_report(
        protocol="cwt",
        revision=CURRENT_VERSION.value,
        features=tuple(FEATURES_BY_VERSION[CURRENT_VERSION.value]),
        evidence_links=("tests/unit/test_cwt_standalone_claim_packages.py",),
        extra_requirements=CAPABILITY_REQUIREMENTS,
        include_default_artifact_requirements=False,
    )


__all__ = [
    "CAPABILITY_REQUIREMENTS",
    "COMPATIBILITY_PATHS",
    "CURRENT_VERSION",
    "CWT_CARRIER",
    "CWT_REGISTERED_CLAIMS",
    "CWT_CLAIM_BY_LABEL",
    "CWT_EXTENSION_CLAIMS",
    "build_cwt_claims",
    "CWT_LABEL_BY_CLAIM",
    "CwtClaimBinding",
    "FEATURES_BY_VERSION",
    "VERSION_HISTORY",
    "VERSION_PUBLISHED",
    "VERSION_STATUS",
    "CwtCarrier",
    "CwtCompatibility",
    "CwtVersion",
    "UnsupportedCwtMediaTypeError",
    "capability_report",
    "compatibility",
    "compose_cwt_claim_set",
    "cwt_label_for",
    "migrate_claims",
    "select_carrier",
    "select_version",
    "supports",
]
