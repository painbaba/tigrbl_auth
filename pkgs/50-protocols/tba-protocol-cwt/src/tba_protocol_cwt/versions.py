"""RFC 8392 version ownership."""

from tba_primitives_identity.enum_compat import StrEnum


class CwtVersion(StrEnum):
    RFC8392 = "RFC8392"


CURRENT_VERSION = CwtVersion.RFC8392
VERSION_HISTORY = (CwtVersion.RFC8392,)
VERSION_STATUS = {CwtVersion.RFC8392.value: "standards-track"}
VERSION_PUBLISHED = {CwtVersion.RFC8392.value: "2018-05"}


def select_version(identifier: str = CURRENT_VERSION.value) -> CwtVersion:
    try:
        return CwtVersion(identifier)
    except ValueError as exc:
        raise ValueError(f"unsupported CWT version: {identifier}") from exc


__all__ = [
    "CURRENT_VERSION",
    "VERSION_HISTORY",
    "VERSION_PUBLISHED",
    "VERSION_STATUS",
    "CwtVersion",
    "select_version",
]
