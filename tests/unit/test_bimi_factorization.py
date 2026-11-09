from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

pytest.importorskip("tba_capability_communications_identity")
pytest.importorskip("tba_profile_communications_identity_bimi")

from tba_capability_communications_identity import (
    DomainCheck,
    DomainOutcome,
    assess_domain_onboarding,
    recheck_domain,
)
from tba_codec_x509_logotype import decode_subject_logotype
from tba_contracts_dns import TxtResult, TxtStatus
from tba_profile_communications_identity_bimi import (
    BimiProfile,
    CertificateOutcome,
    CheckOutcome,
    MarkType,
    MarkVerification,
)
from tba_profile_communications_identity_bimi.capability_adapter import (
    BimiDomainChecker,
)
from tba_protocol_bimi import AssertionStatus, discover_assertion
from tba_protocol_dmarc import (
    PolicyStatus,
    discover_policy,
    effective_policy,
    parse_policy_record,
)
from tba_provider_certificate_evidence import (
    PathValidationError,
    load_crls,
    verify_chain,
)
from tba_provider_dns_txt.contracts import TxtResult as LegacyTxtResult
from tba_provider_dns_txt.contracts import TxtStatus as LegacyTxtStatus

from tests.fixtures.bimi.mark_certificates import AT, LOGOTYPE, make_evidence


def _dns(records):
    dns = Mock()
    dns.lookup_txt.side_effect = lambda name: (
        TxtResult(TxtStatus.FOUND, (records[name],))
        if name in records
        else TxtResult(TxtStatus.ABSENT)
    )
    return dns


def test_dns_contract_exports_remain_identical():
    assert LegacyTxtResult is TxtResult
    assert LegacyTxtStatus is TxtStatus


def test_protocol_discovers_psd_policy_but_profile_requires_organizational_enforcement():
    dns = _dns({"_dmarc.test": b"v=DMARC1; p=reject; sp=quarantine; np=reject; psd=y"})
    policy = discover_policy(dns, "news.example.test", author_exists=False)
    assert policy.status is PolicyStatus.FOUND
    assert policy.policy_source == "_dmarc.test"
    assert policy.organizational_domain == "example.test"
    assert policy.organizational_record is None
    assert policy.effective_policy == "reject"

    profile = BimiProfile(dns=dns, validator=Mock())
    assert (
        profile.check_readiness("news.example.test").dmarc.outcome
        is CheckOutcome.MISSING
    )

    record = parse_policy_record(b"v=DMARC1; p=none; sp=quarantine; t=y; pct=25")
    assert effective_policy(record, inherited=True) == "quarantine"
    assert record.testing
    assert record.legacy_percentage == 25


def test_bimi_protocol_discovers_assertions_independently_of_dmarc():
    dns = _dns(
        {
            "spring.sales._bimi.example.test": b"v=BIMI1; l=https://example.test/logo.svg",
        }
    )
    result = discover_assertion(
        dns, "mail.example.test", "spring.sales", "example.test"
    )
    assert result.status is AssertionStatus.FOUND
    assert result.assertion.name == "spring.sales._bimi.example.test"
    assert result.assertion.evidence_url is None
    with pytest.raises(ValueError, match="must contain"):
        discover_assertion(dns, "mail.example.test", organizational_domain="other.test")


def test_logotype_codec_decodes_without_enforcing_bimi_logo_policy():
    leaf, *_ = make_evidence(corrupt_digest=True)
    logo = decode_subject_logotype(
        leaf.extensions.get_extension_for_oid(LOGOTYPE).value.value
    )
    assert logo is not None
    (image,) = logo.images
    assert image.media_type == "image/svg+xml"
    assert image.digests[0].digest == bytes(32)


def test_generic_evidence_verifier_exposes_revocation_without_bimi_policy():
    leaf, issuer, root, crls, _ = make_evidence(revoke_issuer=True, issuer_eku=False)
    chain = verify_chain(leaf, [issuer], [root], AT)
    assert chain == [leaf, issuer, root]
    evidence = load_crls(chain, crls.get, AT)
    with pytest.raises(PathValidationError) as error:
        verify_chain(leaf, [issuer], [root], AT, evidence)
    assert error.value.revoked


@pytest.mark.asyncio
async def test_workflow_uses_same_contract_for_a_different_profile():
    checker = Mock(profile="example-channel")
    checker.check.return_value = DomainCheck("example.test", DomainOutcome.NOT_READY)
    audit = AsyncMock()
    tenant_id = uuid4()
    db = object()

    result = await recheck_domain(
        "example.test",
        checker=checker,
        audit=audit,
        db=db,
        tenant_id=tenant_id,
    )

    assert result.outcome is DomainOutcome.NOT_READY
    audit.assert_awaited_once_with(
        db=db,
        tenant_id=tenant_id,
        event_type="communications_identity.domain.rechecked",
        target_type="sending_domain",
        target_id="example.test",
        outcome="not_ready",
        details={"profile": "example-channel"},
    )


@pytest.mark.asyncio
async def test_bimi_workflow_uses_discovered_owner_and_audits_recheck():
    dns = _dns(
        {
            "_dmarc.example.test": b"v=DMARC1; p=reject",
            "default._bimi.example.test": b"v=BIMI1; l=https://example.test/logo.svg; a=https://example.test/mark.pem",
        }
    )
    profile = BimiProfile(dns=dns, validator=Mock())
    profile.verify_certificate = Mock(
        return_value=MarkVerification(
            CertificateOutcome.VALID,
            MarkType.CMC,
            sha256="fixture-digest",
        )
    )
    evidence = Mock(side_effect=[b"fixture certificate", None])
    checker = BimiDomainChecker(profile, evidence=evidence)
    tenant_id = uuid4()
    audit = AsyncMock()

    initial = await assess_domain_onboarding(
        "News.Example.test",
        checker=checker,
        audit=audit,
        db=None,
        tenant_id=tenant_id,
    )
    later = await recheck_domain(
        "News.Example.test",
        checker=checker,
        audit=audit,
        db=None,
        tenant_id=tenant_id,
    )

    assert initial.outcome is DomainOutcome.READY
    assert later.outcome is DomainOutcome.INDETERMINATE
    profile.verify_certificate.assert_called_once_with(
        b"fixture certificate",
        assertion_name="default._bimi.example.test",
    )
    initial_event, later_event = (call.kwargs for call in audit.await_args_list)
    assert initial_event["tenant_id"] == later_event["tenant_id"] == tenant_id
    assert (
        initial_event["event_type"]
        == "communications_identity.domain.onboarding_assessed"
    )
    assert initial_event["details"]["mark_type"] == "cmc"
    assert later_event["details"]["certificate"] == "unavailable"


@pytest.mark.asyncio
async def test_workflow_requires_explicit_tenant_before_checking_or_auditing():
    checker = Mock()
    audit = AsyncMock()
    with pytest.raises(ValueError, match="explicit tenant"):
        await recheck_domain(
            "example.test", checker=checker, audit=audit, db=None, tenant_id=None
        )
    checker.check.assert_not_called()
    audit.assert_not_awaited()
