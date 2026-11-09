from asn1crypto import algos, core

from .types import LogotypeDigest, LogotypeImage, LogotypeReference, SubjectLogotype


class _HashValue(core.Sequence):
    _fields = [
        ("algorithm", algos.DigestAlgorithm),
        ("digest", core.OctetString),
    ]


class _Hashes(core.SequenceOf):
    _child_spec = _HashValue


class _Uris(core.SequenceOf):
    _child_spec = core.IA5String


class _Details(core.Sequence):
    _fields = [
        ("media_type", core.IA5String),
        ("hashes", _Hashes),
        ("uris", _Uris),
    ]


class _Image(core.Sequence):
    _fields = [
        ("details", _Details),
        ("info", core.Sequence, {"optional": True}),
    ]


class _Images(core.SequenceOf):
    _child_spec = _Image


class _Data(core.Sequence):
    _fields = [
        ("images", _Images, {"optional": True}),
        ("audio", core.Sequence, {"implicit": 1, "optional": True}),
    ]


class _Reference(core.Sequence):
    _fields = [("hashes", _Hashes), ("uris", _Uris)]


class _Logo(core.Choice):
    _alternatives = [
        ("direct", _Data, {"implicit": 0}),
        ("indirect", _Reference, {"implicit": 1}),
    ]


class _Logotypes(core.Sequence):
    _fields = [
        ("community", core.Sequence, {"explicit": 0, "optional": True}),
        ("issuer", _Logo, {"explicit": 1, "optional": True}),
        ("subject", _Logo, {"explicit": 2, "optional": True}),
        ("other", core.Sequence, {"explicit": 3, "optional": True}),
    ]


def _digests(details: core.Sequence) -> tuple[LogotypeDigest, ...]:
    return tuple(
        LogotypeDigest(entry["algorithm"]["algorithm"].native, entry["digest"].native)
        for entry in details["hashes"]
    )


def decode_subject_logotype(extension: bytes) -> SubjectLogotype | None:
    """Decode the subject logo from the DER-encoded extension value."""
    subject = _Logotypes.load(extension, strict=True)["subject"]
    if isinstance(subject, core.Void):
        return None
    data = subject.chosen
    if subject.name == "indirect":
        return SubjectLogotype(
            reference=LogotypeReference(_digests(data), tuple(data["uris"].native))
        )
    images = data["images"]
    decoded = []
    if not isinstance(images, core.Void):
        for image in images:
            details = image["details"]
            decoded.append(
                LogotypeImage(
                    details["media_type"].native,
                    _digests(details),
                    tuple(details["uris"].native),
                )
            )
    return SubjectLogotype(tuple(decoded), not isinstance(data["audio"], core.Void))
