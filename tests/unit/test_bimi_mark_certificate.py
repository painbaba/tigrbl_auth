from datetime import timedelta

import pytest

pytest.importorskip("tba_provider_bimi_mark_certificate")

from cryptography.hazmat.primitives.serialization import Encoding
from tba_contracts_security_trust import (
    CertificateProfile,
    CertificateStatus,
    TrustAnchor,
)
from tba_profile_communications_identity_bimi import (
    CertificateOutcome,
    MarkType,
    verify_certificate,
)
from tba_provider_bimi_mark_certificate import MarkCertificatePathBackend
from tba_provider_certificate_path_validator import ProfiledCertificatePathValidator
from tba_provider_certificate_status import SnapshotCertificateStatusProvider
from tba_provider_trust_anchor import ProfiledTrustAnchorProvider

from tests.fixtures.bimi.mark_certificates import AT, LEAF_CRL, SVG, make_evidence


def _verify(
    *,
    owner="default._bimi.example.com",
    via_dispatch=False,
    logs=True,
    missing_crl=False,
    trust=True,
    at=AT,
    **fixture,
):
    leaf, issuer, root, crls, log = make_evidence(**fixture)
    if missing_crl:
        del crls[LEAF_CRL]
    anchors = ProfiledTrustAnchorProvider()
    profiles = (
        CertificateProfile.BIMI_MARK if trust else CertificateProfile.X509_SVID,
    )
    anchors.publish(TrustAnchor("fixture", root.public_bytes(Encoding.DER), profiles))
    backend = MarkCertificatePathBackend(
        anchors=anchors,
        crl_source=crls.get,
        ct_logs=[log] if logs else [],
    )
    validator = backend
    if via_dispatch:
        snapshot = SnapshotCertificateStatusProvider()
        snapshot.publish(
            leaf.public_bytes(Encoding.DER), CertificateStatus.GOOD, "fixture", AT
        )
        validator = ProfiledCertificatePathValidator(
            anchors, snapshot, {CertificateProfile.BIMI_MARK: backend}
        )
    return verify_certificate(
        leaf.public_bytes(Encoding.PEM) + issuer.public_bytes(Encoding.PEM),
        assertion_name=owner,
        validator=validator,
        validation_time=at,
    )


@pytest.mark.parametrize(
    ("mark", "kind"),
    [
        ("Registered Mark", MarkType.VMC),
        ("Government Mark", MarkType.VMC),
        ("Prior Use Mark", MarkType.CMC),
        ("Modified Registered Mark", MarkType.CMC),
        ("Provisional Mark", MarkType.CMC),
    ],
)
def test_valid_mark_certificate_with_profiled_tba_providers(mark, kind):
    result = _verify(mark=mark, via_dispatch=True)
    assert result.outcome is CertificateOutcome.VALID, result.errors
    assert result.mark_type is kind
    assert result.trust_anchor_id == "fixture"
    assert len(result.sha256) == 64


@pytest.mark.parametrize(
    ("options", "error"),
    [
        ({"owner": "default._bimi.news.example.com"}, "SAN"),
        ({"san": "*.example.com", "owner": "default._bimi.news.example.com"}, "SAN"),
        ({"san": "other._bimi.example.com"}, "SAN"),
        ({"mark": "Unknown Mark"}, "mark type"),
        ({"corrupt_digest": True}, "digest"),
        ({"svg": SVG.replace(b"<rect ", b"<script/><rect ")}, "active"),
        ({"issuer_eku": False}, "EKU"),
        ({"revoke_leaf": True}, "revoked"),
        ({"revoke_issuer": True}, "revoked"),
        ({"corrupt_sct": True}, "SCT signature"),
        ({"at": AT + timedelta(days=31)}, "path validation failed"),
    ],
)
def test_invalid_mark_evidence(options, error):
    result = _verify(**options)
    assert result.outcome is CertificateOutcome.INVALID
    assert error in result.errors[0]


def test_selector_bound_san_matches_exact_assertion():
    result = _verify(san="news._bimi.example.com", owner="news._bimi.example.com")
    assert result.outcome is CertificateOutcome.VALID, result.errors


@pytest.mark.parametrize(
    ("options", "error"),
    [
        ({"missing_crl": True}, "CRL coverage"),
        ({"stale": True}, "CRL coverage"),
        ({"logs": False}, "configured CT log"),
        ({"trust": False}, "trust anchors"),
    ],
)
def test_incomplete_evidence_is_indeterminate(options, error):
    result = _verify(**options)
    assert result.outcome is CertificateOutcome.INDETERMINATE
    assert error in result.errors[0]
