import pytest

pytest.importorskip("tba_profile_communications_identity_bimi")

from tba_profile_communications_identity_bimi import CheckOutcome, check_readiness
from tba_provider_dns_txt import TxtResult, TxtStatus

ASSERTION = b"v=BIMI1; l=https://example.com/logo.svg; a=https://example.com/mark.pem"
POLICY = b"v=DMARC1; p=reject; sp=quarantine"


class FixtureDns:
    def __init__(self, records):
        self.records = records
        self.lookups = []

    def lookup_txt(self, name):
        self.lookups.append(name)
        records = self.records.get(name)
        if records is None:
            return TxtResult(TxtStatus.ABSENT)
        if records is TxtStatus.TEMPORARY_FAILURE:
            return TxtResult(records)
        return TxtResult(TxtStatus.FOUND, records)


def test_readiness_falls_back_to_same_selector_at_organization():
    dns = FixtureDns(
        {
            "_dmarc.example.com": (POLICY,),
            "marketing._bimi.example.com": (ASSERTION,),
        }
    )
    result = check_readiness("News.Example.com.", selector="Marketing", dns=dns)
    assert result.ready
    assert result.assertion_name == "marketing._bimi.example.com"
    assert result.dmarc.policy_source == "_dmarc.example.com"
    assert result.dmarc.effective_policy == "quarantine"
    assert "default._bimi.example.com" not in dns.lookups


@pytest.mark.parametrize(
    "policy",
    [
        b"v=DMARC1; p=none",
        b"v=DMARC1; p=reject; sp=none",
        b"v=DMARC1; p=quarantine; pct=25",
        b"v=DMARC1; p=reject; t=y",
        b"v=DMARC1; p=reject; p=quarantine",
    ],
)
def test_dmarc_readiness_fails_closed(policy):
    result = check_readiness(
        "example.com",
        dns=FixtureDns(
            {
                "_dmarc.example.com": (policy,),
                "default._bimi.example.com": (ASSERTION,),
            }
        ),
    )
    assert not result.ready
    assert result.bimi.outcome is CheckOutcome.PASS
    assert result.dmarc.outcome is CheckOutcome.FAIL


@pytest.mark.parametrize(
    ("records", "expected"),
    [
        ((b"v=BIMI1; l=; a=",), CheckOutcome.DECLINED),
        ((ASSERTION, ASSERTION), CheckOutcome.FAIL),
        ((b"v=BIMI1; l=http://example.com/logo.svg",), CheckOutcome.FAIL),
        (TxtStatus.TEMPORARY_FAILURE, CheckOutcome.INDETERMINATE),
    ],
)
def test_author_assertion_failure_does_not_fall_back(records, expected):
    dns = FixtureDns(
        {
            "_dmarc.example.com": (POLICY,),
            "default._bimi.example.com": (ASSERTION,),
            "default._bimi.news.example.com": records,
        }
    )
    result = check_readiness("news.example.com", dns=dns)
    assert result.bimi.outcome is expected
    assert "default._bimi.example.com" not in dns.lookups


def test_self_assertion_is_discovered_without_mark_certificate_readiness():
    result = check_readiness(
        "example.com",
        dns=FixtureDns(
            {
                "_dmarc.example.com": (POLICY,),
                "default._bimi.example.com": (
                    b"v=BIMI1; l=https://example.com/logo.svg",
                ),
            }
        ),
    )
    assert result.bimi.outcome is CheckOutcome.PASS
    assert not result.ready


def test_dmarc_tree_walk_is_bounded():
    dns = FixtureDns({})
    check_readiness("a.b.c.d.e.f.g.h.i.j.example.com", dns=dns)
    assert len([name for name in dns.lookups if name.startswith("_dmarc.")]) == 8


def test_organizational_policy_must_enforce_even_when_author_policy_rejects():
    result = check_readiness(
        "news.example.com",
        selector="spring.sales",
        dns=FixtureDns(
            {
                "_dmarc.news.example.com": (b"v=DMARC1; p=reject",),
                "_dmarc.example.com": (b"v=DMARC1; p=none",),
                "spring.sales._bimi.news.example.com": (ASSERTION,),
            }
        ),
    )
    assert result.assertion_name == "spring.sales._bimi.news.example.com"
    assert result.dmarc.organizational_domain == "example.com"
    assert result.dmarc.policy_source == "_dmarc.news.example.com"
    assert result.dmarc.effective_policy == "reject"
    assert result.dmarc.outcome is CheckOutcome.FAIL


def test_dmarc_temporary_failure_is_distinct_from_no_policy():
    result = check_readiness(
        "example.com",
        dns=FixtureDns(
            {
                "_dmarc.example.com": TxtStatus.TEMPORARY_FAILURE,
                "default._bimi.example.com": (ASSERTION,),
            }
        ),
    )
    assert result.bimi.outcome is CheckOutcome.PASS
    assert result.dmarc.outcome is CheckOutcome.INDETERMINATE
    assert not result.ready
