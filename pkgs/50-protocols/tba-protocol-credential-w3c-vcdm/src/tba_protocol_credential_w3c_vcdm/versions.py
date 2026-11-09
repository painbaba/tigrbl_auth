from tba_primitives_identity.enum_compat import StrEnum


class VcdmVersion(StrEnum):
    V1_1 = "1.1"
    V2_0 = "2.0"


CURRENT_VERSION = VcdmVersion.V2_0
VERSION_HISTORY = {
    VcdmVersion.V1_1.value: {
        "status": "recommendation",
        "specification": "https://www.w3.org/TR/vc-data-model/",
    },
    VcdmVersion.V2_0.value: {
        "status": "recommendation",
        "specification": "https://www.w3.org/TR/vc-data-model-2.0/",
    },
}


def select_version(value: str | VcdmVersion) -> VcdmVersion:
    return VcdmVersion(value)


__all__ = ["CURRENT_VERSION", "VERSION_HISTORY", "VcdmVersion", "select_version"]
