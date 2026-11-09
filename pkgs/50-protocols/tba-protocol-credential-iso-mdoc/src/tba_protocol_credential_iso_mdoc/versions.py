from dataclasses import dataclass
from tba_primitives_identity.enum_compat import StrEnum


class IsoMdocVersion(StrEnum):
    ISO_18013_5_2021 = "ISO/IEC 18013-5:2021"


@dataclass(frozen=True, slots=True)
class IsoMdocRevision:
    identifier: str
    status: str
    specification: str


CURRENT_VERSION = IsoMdocVersion.ISO_18013_5_2021
VERSION_HISTORY = {
    CURRENT_VERSION.value: IsoMdocRevision(
        CURRENT_VERSION.value,
        "international-standard",
        "ISO/IEC 18013-5:2021",
    )
}


def select_version(value: str | IsoMdocVersion) -> IsoMdocVersion:
    version = IsoMdocVersion(value)
    if version.value not in VERSION_HISTORY:
        raise ValueError(f"unsupported ISO mdoc revision: {value}")
    return version


__all__ = [
    "CURRENT_VERSION",
    "VERSION_HISTORY",
    "IsoMdocRevision",
    "IsoMdocVersion",
    "select_version",
]
