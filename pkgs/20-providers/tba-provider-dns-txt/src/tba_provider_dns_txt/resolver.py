import math

import dns.exception
import dns.resolver

from .contracts import TxtResult, TxtStatus


class DnsTxtResolver:
    def __init__(
        self, *, timeout: float = 3, resolver: dns.resolver.Resolver | None = None
    ) -> None:
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("DNS timeout must be finite and positive")
        self._timeout = timeout
        self._resolver = resolver if resolver is not None else dns.resolver.Resolver()

    def lookup_txt(self, name: str, /) -> TxtResult:
        try:
            answer = self._resolver.resolve(
                name.removesuffix(".") + ".",
                "TXT",
                search=False,
                lifetime=self._timeout,
            )
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            return TxtResult(TxtStatus.ABSENT)
        except (dns.exception.Timeout, dns.resolver.NoNameservers):
            return TxtResult(TxtStatus.TEMPORARY_FAILURE)
        return TxtResult(
            TxtStatus.FOUND, tuple(b"".join(record.strings) for record in answer)
        )
