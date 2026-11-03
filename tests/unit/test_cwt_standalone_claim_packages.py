import pytest

from tba_protocol_cwt import (
    CAPABILITY_REQUIREMENTS,
    CURRENT_VERSION,
    CWT_CARRIER,
    CWT_REGISTERED_CLAIMS,
    CwtVersion,
    UnsupportedCwtMediaTypeError,
    capability_report,
    compatibility,
    compose_cwt_claim_set,
    cwt_label_for,
    migrate_claims,
    select_carrier,
    supports,
)
from tba_concrete_claim_issuer import IssuerClaim


def test_cwt_registered_claims_map_integer_labels_to_semantic_claims():
    assert {binding.label for binding in CWT_REGISTERED_CLAIMS} == set(range(1, 8))
    assert {binding.semantic_name for binding in CWT_REGISTERED_CLAIMS} == {
        "iss",
        "sub",
        "aud",
        "exp",
        "nbf",
        "iat",
        "jti",
    }
    assert cwt_label_for(IssuerClaim) == 1
    assert cwt_label_for(IssuerClaim("issuer")) == 1


def test_cwt_claim_set_uses_canonical_claim_objects_and_explicit_rfc_version():
    claim_set = compose_cwt_claim_set(IssuerClaim("issuer"))
    assert CURRENT_VERSION is CwtVersion.RFC8392
    assert claim_set.protocol == "cwt"
    assert claim_set.version == "RFC8392"
    assert isinstance(claim_set.claims[0], IssuerClaim)


def test_cwt_owns_revision_features_compatibility_and_migration_entry_point():
    assert supports("cose-protection")
    assert compatibility("RFC8392").compatible
    assert not compatibility("draft-cwt").compatible
    assert migrate_claims({1: "issuer"}, source="RFC8392") == {1: "issuer"}
    with pytest.raises(ValueError, match="unsupported CWT migration"):
        migrate_claims({}, source="draft-cwt")


def test_cwt_owns_carrier_errors_and_explicit_capability_bindings():
    assert select_carrier("application/cwt") is CWT_CARRIER
    with pytest.raises(UnsupportedCwtMediaTypeError):
        select_carrier("application/jwt")
    assert {requirement.operation for requirement in CAPABILITY_REQUIREMENTS} == {
        "decode",
        "encode",
        "validate",
    }
    assert capability_report()["selected_revision"] == "RFC8392"


def test_draft_extensions_are_mapped_and_encoded_without_integer_assignments():
    import hashlib
    from tba_concrete_claim_authorization_context import AuthorizationContextClaim
    from tba_concrete_claim_access_token_digest import AccessTokenDigestClaim
    from tba_concrete_claim_issued_at import IssuedAtClaim
    from tba_concrete_cwt import CWT_CLAIM_LABELS, decode_cwt_claims
    from tba_protocol_cwt import CWT_CLAIM_BY_LABEL, build_cwt_claims

    digest = hashlib.sha256(b"token").digest()
    context = AuthorizationContextClaim({"type": "moqt", "action": "SUBSCRIBE"})
    ath = AccessTokenDigestClaim.from_cwt_value(digest)
    for claim in (context, ath):
        assert cwt_label_for(claim) == claim.name
        assert CWT_CLAIM_BY_LABEL[claim.name] is type(claim)
        assert CWT_CLAIM_LABELS[claim.name] == claim.name
    encoded = build_cwt_claims(context, ath, IssuedAtClaim(123),
                               actx_field_labels={"action": 1}).encode()
    decoded = decode_cwt_claims(encoded)
    assert decoded.get_registered("actx") == {0: "moqt", 1: "SUBSCRIBE"}
    assert decoded.get_registered("ath") == digest
    assert decoded.get_registered("iat") == 123
    with pytest.raises(ValueError, match="duplicate"):
        build_cwt_claims(ath, ath)


def test_cwt_profile_accepts_extension_keys_and_reports_mixed_missing_labels():
    from tba_protocol_cwt.profile import CwtProfile
    profile = CwtProfile("draft-proof", frozenset({6, "actx", "ath"}), frozenset({"Sign1"}))
    profile.validate({6: 123, "actx": {0: "moqt"}, "ath": b"x" * 32}, "Sign1")
    with pytest.raises(ValueError, match="missing required CWT claim labels"):
        profile.validate({}, "Sign1")
