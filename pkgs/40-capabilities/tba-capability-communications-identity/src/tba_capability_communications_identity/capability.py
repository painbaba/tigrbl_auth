from tba_concrete_capability import Capability
from tba_contracts_identity.capabilities import CapabilityDefinition, CapabilityOperation

from .onboarding import assess_domain_onboarding
from .recheck import recheck_domain


class CommunicationsIdentityCapability(Capability):
    """Compose domain assessment, recheck, and audit operations."""

    def __init__(self) -> None:
        super().__init__(
            CapabilityDefinition("communications.identity", "1.0"),
            operations={
                "assess_domain_onboarding": CapabilityOperation(
                    target=assess_domain_onboarding, delegated=True
                ),
                "recheck_domain": CapabilityOperation(target=recheck_domain, delegated=True),
            },
        )
