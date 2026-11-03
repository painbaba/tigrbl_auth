"""Authentication and federation table aliases for capability composition."""

from tba_storage_authentication.tables import AuthenticationChallenge, Credential, CredentialMfaFactor, CredentialRecoveryCode
from tba_storage_federation.tables import FederatedSession, Federation, IdentityProvider

AuthenticationChallengeTable = AuthenticationChallenge
CredentialTable = Credential
CredentialMfaFactorTable = CredentialMfaFactor
CredentialRecoveryCodeTable = CredentialRecoveryCode
FederatedSessionTable = FederatedSession
FederationTable = Federation
IdentityProviderTable = IdentityProvider

__all__ = [
    "AuthenticationChallengeTable",
    "CredentialMfaFactorTable",
    "CredentialRecoveryCodeTable",
    "CredentialTable",
    "FederatedSessionTable",
    "FederationTable",
    "IdentityProviderTable",
]
