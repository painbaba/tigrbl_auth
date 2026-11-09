"""Run the optional BIMI DNS preflight or verify a local Mark Certificate bundle."""

import argparse
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding
from tba_contracts_security_trust import CertificateProfile, TrustAnchor
from tba_profile_communications_identity_bimi import (
    CertificateOutcome,
    check_readiness,
    verify_certificate,
)
from tba_provider_bimi_mark_certificate import MarkCertificatePathBackend
from tba_provider_dns_txt import DnsTxtResolver
from tba_provider_trust_anchor import ProfiledTrustAnchorProvider


def _crl_location(value: str) -> tuple[str, Path]:
    url, separator, filename = value.rpartition("=")
    if not separator or not url or not filename:
        raise argparse.ArgumentTypeError("use CRL_URL=LOCAL_FILE")
    return url, Path(filename)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    dns = commands.add_parser("dns", help="Check BIMI and DMARC DNS readiness")
    dns.add_argument("domain")
    dns.add_argument("--selector", default="default")
    dns.add_argument("--organizational-domain")
    dns.add_argument("--timeout", type=float, default=3)

    verify = commands.add_parser("verify", help="Verify a supplied CMC or VMC")
    verify.add_argument(
        "assertion_name", help="The assertion owner reported by DNS discovery"
    )
    verify.add_argument("bundle", type=Path, help="Leaf-first PEM certificate bundle")
    verify.add_argument("--root", action="append", type=Path, required=True)
    verify.add_argument("--crl", action="append", type=_crl_location, required=True)
    verify.add_argument("--ct-log", action="append", type=Path, required=True)
    verify.add_argument(
        "--at", type=datetime.fromisoformat, help="ISO 8601 verification time"
    )

    args = parser.parse_args()
    try:
        if args.command == "dns":
            result = check_readiness(
                args.domain,
                dns=DnsTxtResolver(timeout=args.timeout),
                selector=args.selector,
                organizational_domain=args.organizational_domain,
            )
            print(json.dumps({**asdict(result), "ready": result.ready}, indent=2))
            return 0 if result.ready else 1

        anchors = ProfiledTrustAnchorProvider()
        for filename in args.root:
            root = x509.load_pem_x509_certificate(filename.read_bytes())
            anchors.publish(
                TrustAnchor(
                    str(filename),
                    root.public_bytes(Encoding.DER),
                    (CertificateProfile.BIMI_MARK,),
                )
            )
        crls = {url: filename.read_bytes() for url, filename in args.crl}
        validator = MarkCertificatePathBackend(
            anchors=anchors,
            crl_source=crls.get,
            ct_logs=[filename.read_bytes() for filename in args.ct_log],
        )
        result = verify_certificate(
            args.bundle.read_bytes(),
            assertion_name=args.assertion_name,
            validator=validator,
            validation_time=args.at,
        )
        print(json.dumps(asdict(result), indent=2))
        return 0 if result.outcome is CertificateOutcome.VALID else 1
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
