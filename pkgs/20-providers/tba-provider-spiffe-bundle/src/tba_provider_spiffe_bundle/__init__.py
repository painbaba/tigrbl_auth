from tba_contracts_workload_identity import SpiffeTrustBundle, TrustDomain
from tba_bases_workload_identity import TrustBundleProviderBase


class VersionedSpiffeBundleProvider(TrustBundleProviderBase):
    def __init__(self):
        self._bundles: dict[TrustDomain, SpiffeTrustBundle] = {}

    def publish(self, bundle: SpiffeTrustBundle) -> None:
        current = self._bundles.get(bundle.trust_domain)
        if current is not None and current.version >= bundle.version:
            raise ValueError("SPIFFE bundle version must advance")
        if not bundle.x509_authorities and not bundle.jwt_authorities:
            raise ValueError("SPIFFE bundle must contain an authority")
        self._bundles[bundle.trust_domain] = bundle

    def bundle_for(self, trust_domain: TrustDomain, /) -> SpiffeTrustBundle:
        try:
            return self._bundles[trust_domain]
        except KeyError as exc:
            raise LookupError(trust_domain.name) from exc


__all__ = ["VersionedSpiffeBundleProvider"]
