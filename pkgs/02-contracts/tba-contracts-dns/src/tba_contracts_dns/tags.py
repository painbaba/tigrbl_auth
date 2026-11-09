import re


def versioned_records(records: tuple[bytes, ...], version: bytes) -> tuple[bytes, ...]:
    pattern = rb"^[ \t]*[vV][ \t]*=[ \t]*" + re.escape(version) + rb"[ \t]*(?:;|$)"
    return tuple(record for record in records if re.match(pattern, record))


def parse_tags(record: bytes) -> dict[str, str]:
    if len(record) > 4096:
        raise ValueError("TXT record exceeds the supported size")
    tags: dict[str, str] = {}
    for item in record.decode("ascii").strip(" \t").removesuffix(";").split(";"):
        key, separator, value = item.partition("=")
        key = key.strip(" \t").lower()
        value = value.strip(" \t")
        if (
            not separator
            or not re.fullmatch(r"[a-z][a-z0-9]*", key)
            or key in tags
            or any(ord(char) < 32 or ord(char) == 127 for char in value)
        ):
            raise ValueError("malformed or duplicate TXT tag")
        tags[key] = value
    return tags
