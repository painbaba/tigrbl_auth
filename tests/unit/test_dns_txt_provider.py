from unittest.mock import Mock

import pytest

pytest.importorskip("tba_provider_dns_txt")

import dns.exception
import dns.resolver
from tba_provider_dns_txt import DnsTxtResolver, TxtResult, TxtStatus


def test_dns_joins_segments_only_within_each_txt_record():
    transport = Mock()
    transport.resolve.return_value = [Mock(strings=(b"a", b"b")), Mock(strings=(b"c",))]
    result = DnsTxtResolver(timeout=1, resolver=transport).lookup_txt("example.com")
    assert result == TxtResult(TxtStatus.FOUND, (b"ab", b"c"))
    transport.resolve.assert_called_once_with(
        "example.com.", "TXT", search=False, lifetime=1
    )


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (dns.resolver.NXDOMAIN, TxtStatus.ABSENT),
        (dns.resolver.NoAnswer, TxtStatus.ABSENT),
        (dns.exception.Timeout, TxtStatus.TEMPORARY_FAILURE),
        (dns.resolver.NoNameservers, TxtStatus.TEMPORARY_FAILURE),
    ],
)
def test_dns_distinguishes_missing_and_temporary_failure(error, status):
    transport = Mock()
    transport.resolve.side_effect = error
    assert DnsTxtResolver(resolver=transport).lookup_txt("example.com").status is status
