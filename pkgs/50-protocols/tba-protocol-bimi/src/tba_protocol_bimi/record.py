import re
from urllib.parse import urlsplit

from tba_contracts_dns import parse_tags, versioned_records

from .types import BimiAssertion

_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", re.ASCII)


def normalize_selector(selector: str) -> str:
    selector = selector.lower()
    if not all(_LABEL.fullmatch(label) for label in selector.split(".")):
        raise ValueError("invalid BIMI selector")
    return selector


def assertion_owner(selector: str, domain: str) -> str:
    owner = f"{selector}._bimi.{domain}"
    if len(owner) > 253:
        raise ValueError("BIMI assertion owner exceeds the DNS name limit")
    return owner


def _https_url(value: str) -> str | None:
    if not value:
        return None
    if any(char.isspace() for char in value) or "\\" in value:
        raise ValueError("invalid BIMI URL")
    url = urlsplit(value)
    if (
        url.scheme != "https"
        or not url.hostname
        or url.username is not None
        or url.password is not None
        or url.fragment
        or url.port == 0
    ):
        raise ValueError("BIMI asset locations require an HTTPS URL")
    return value


def parse_assertion(record: bytes, *, name: str) -> BimiAssertion:
    if not versioned_records((record,), b"BIMI1"):
        raise ValueError("unsupported BIMI record version")
    tags = parse_tags(record)
    if "l" not in tags:
        raise ValueError("BIMI record is missing the l tag")
    logo = _https_url(tags["l"])
    evidence = _https_url(tags.get("a", ""))
    if not logo and evidence:
        raise ValueError("BIMI evidence requires a logo location")
    return BimiAssertion(name, logo, evidence)
