from collections.abc import Callable, Iterable

from tba_contracts_workload_identity import Svid, SvidFormat, WorkloadSelector
from tba_bases_workload_identity import SvidProviderBase
from tba_concrete_svid import normalize_selectors

SelectorSource = Callable[[], Iterable[WorkloadSelector]]


class LocalSpiffeWorkloadApiProvider(SvidProviderBase):
    def __init__(self, selector_source: SelectorSource):
        self._selector_source = selector_source
        self._registrations: dict[
            tuple[WorkloadSelector, ...], dict[SvidFormat, Svid]
        ] = {}

    def register(self, selectors: Iterable[WorkloadSelector], svid: Svid) -> None:
        normalized = normalize_selectors(selectors)
        formats = self._registrations.setdefault(normalized, {})
        if svid.format in formats:
            raise ValueError("SVID format already registered for workload selectors")
        formats[svid.format] = svid

    def fetch_svid(self, audience: str | None = None, /) -> Svid:
        selectors = normalize_selectors(self._selector_source())
        formats = self._registrations.get(selectors)
        if formats is None:
            raise LookupError("no workload registration matches selectors")
        requested_format = SvidFormat.JWT if audience is not None else SvidFormat.X509
        try:
            return formats[requested_format]
        except KeyError as exc:
            raise LookupError(
                f"no {requested_format.value} available for workload"
            ) from exc


__all__ = ["LocalSpiffeWorkloadApiProvider", "SelectorSource"]
