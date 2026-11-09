import base64
import binascii
import gzip
import io
import zlib
from hashlib import new
from xml.etree.ElementTree import ParseError

from tba_codec_x509_logotype import decode_subject_logotype
from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

_MAX_SVG_BYTES = 256 * 1024
_SVG = "{http://www.w3.org/2000/svg}"
_DATA_URL = "data:image/svg+xml;base64,"


def _read_svg(url: str) -> bytes:
    try:
        compressed = base64.b64decode(url[len(_DATA_URL) :], validate=True)
        with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
            svg = stream.read(_MAX_SVG_BYTES + 1)
    except (binascii.Error, OSError, EOFError, zlib.error) as exc:
        raise ValueError("invalid compressed SVG in BIMI logotype") from exc
    if len(svg) > _MAX_SVG_BYTES:
        raise ValueError("BIMI logotype exceeds the SVG size limit")
    return svg.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _check_svg(svg: bytes) -> None:
    try:
        root = ElementTree.fromstring(svg, forbid_dtd=True)
    except (DefusedXmlException, ParseError, LookupError) as exc:
        raise ValueError("invalid or unsafe BIMI logotype SVG") from exc
    if (
        root.tag != _SVG + "svg"
        or root.get("version") != "1.2"
        or root.get("baseProfile") != "tiny-ps"
        or root.find(_SVG + "title") is None
    ):
        raise ValueError("BIMI logotype SVG is missing Tiny P/S document markers")
    for element in root.iter():
        local_name = element.tag.rsplit("}", 1)[-1]
        if not element.tag.startswith(_SVG) or local_name in {
            "script",
            "foreignObject",
            "style",
            "animate",
            "animateMotion",
            "animateTransform",
            "set",
            "discard",
            "handler",
            "listener",
        }:
            raise ValueError("active or foreign content in BIMI logotype SVG")
        for attribute, value in element.attrib.items():
            name = attribute.rsplit("}", 1)[-1].lower()
            if (
                name.startswith("on")
                or name in {"style", "base", "src"}
                or (name == "href" and not value.startswith("#"))
                or ("url(" in value.lower() and not value.lower().startswith("url(#"))
            ):
                raise ValueError("unsupported reference in BIMI logotype SVG")


def verify_subject_logo(extension: bytes) -> None:
    subject = decode_subject_logotype(extension)
    if subject is None or subject.reference is not None:
        raise ValueError("BIMI certificate requires a direct subject logotype")
    if len(subject.images) != 1:
        raise ValueError("BIMI certificate requires one subject logo image")
    if subject.has_audio:
        raise ValueError("BIMI subject logotype cannot contain audio")
    image = subject.images[0]
    urls = [uri for uri in image.uris if uri.startswith(_DATA_URL)]
    if image.media_type != "image/svg+xml" or len(urls) != 1:
        raise ValueError("BIMI logotype requires one embedded SVG image")

    svg = _read_svg(urls[0])
    digests = [
        entry
        for entry in image.digests
        if entry.algorithm in {"sha256", "sha384", "sha512"}
    ]
    if not digests or any(
        new(entry.algorithm, svg).digest() != entry.digest for entry in digests
    ):
        raise ValueError("BIMI logotype digest did not verify")
    _check_svg(svg)
