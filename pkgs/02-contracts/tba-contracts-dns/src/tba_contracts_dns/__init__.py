from .names import normalize_domain
from .tags import parse_tags, versioned_records
from .txt import TxtResolver, TxtResult, TxtStatus

__all__ = [
    "TxtResolver",
    "TxtResult",
    "TxtStatus",
    "normalize_domain",
    "parse_tags",
    "versioned_records",
]
