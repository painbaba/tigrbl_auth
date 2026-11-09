"""Command paths and top-level equality predicates for this profile."""

import re

from .codec import UcanError, canonical_bytes

_COMMAND = re.compile(r"/(?:[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*)?")
_SELECTOR = re.compile(r"\.[A-Za-z_][A-Za-z0-9_]*")


def validate_command(command: str) -> None:
    if (
        not isinstance(command, str)
        or not _COMMAND.fullmatch(command)
        or any(segment in {".", ".."} for segment in command.split("/"))
    ):
        raise UcanError("unsupported command path")


def covers_command(granted: str, requested: str) -> bool:
    return granted == "/" or requested == granted or requested.startswith(granted + "/")


def validate_policy(policy: tuple) -> None:
    for predicate in policy:
        if (
            not isinstance(predicate, (tuple, list))
            or len(predicate) != 3
            or predicate[0] != "=="
            or not isinstance(predicate[1], str)
            or not _SELECTOR.fullmatch(predicate[1])
        ):
            raise UcanError("unsupported UCAN policy predicate")
        canonical_bytes(predicate[2])


def enforce_policy(policy: tuple, arguments: dict) -> None:
    for _, selector, expected in policy:
        # An absent top-level map key resolves to null in UCAN selectors.
        if canonical_bytes(arguments.get(selector[1:])) != canonical_bytes(expected):
            raise UcanError("invocation arguments do not satisfy delegation policy")
