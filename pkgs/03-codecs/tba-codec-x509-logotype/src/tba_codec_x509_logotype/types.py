from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LogotypeDigest:
    algorithm: str
    digest: bytes


@dataclass(frozen=True, slots=True)
class LogotypeImage:
    media_type: str
    digests: tuple[LogotypeDigest, ...]
    uris: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LogotypeReference:
    digests: tuple[LogotypeDigest, ...]
    uris: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SubjectLogotype:
    images: tuple[LogotypeImage, ...] = ()
    has_audio: bool = False
    reference: LogotypeReference | None = None
