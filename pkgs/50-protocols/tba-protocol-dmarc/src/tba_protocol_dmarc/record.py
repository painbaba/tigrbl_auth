import re

from tba_contracts_dns import parse_tags, versioned_records

from .types import DmarcRecord

_POLICIES = {"none", "quarantine", "reject"}


def parse_policy_record(record: bytes) -> DmarcRecord:
    if not versioned_records((record,), b"DMARC1"):
        raise ValueError("unsupported DMARC record version")
    tags = parse_tags(record)
    for key in ("p", "sp", "np"):
        if tags.get(key, "none") not in _POLICIES:
            raise ValueError(f"invalid DMARC {key} policy")
    if "p" not in tags:
        raise ValueError("DMARC record is missing the p policy")
    if tags.get("t", "n") not in {"y", "n"} or tags.get("psd", "u") not in {
        "y",
        "n",
        "u",
    }:
        raise ValueError("invalid DMARC t or psd tag")
    if "pct" in tags and not re.fullmatch(r"[0-9]{1,2}|100", tags["pct"]):
        raise ValueError("invalid legacy DMARC pct tag")
    return DmarcRecord(
        policy=tags["p"],
        subdomain_policy=tags.get("sp"),
        nonexistent_policy=tags.get("np"),
        testing=tags.get("t") == "y",
        legacy_percentage=int(tags.get("pct", "100")),
        public_suffix=tags.get("psd", "u"),
    )
