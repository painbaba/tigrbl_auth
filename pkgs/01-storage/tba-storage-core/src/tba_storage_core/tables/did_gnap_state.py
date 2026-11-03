"""Compatibility exports of domain-owned storage tables."""

from tba_storage_did.tables import DidDocument, DidDocumentVersion, DidVerificationMethod, DidService, DidResolutionCache
from tba_storage_gnap.tables import GnapGrant, GnapContinuation, GnapClientInstance, GnapInteraction

__all__ = ['DidDocument', 'DidDocumentVersion', 'DidVerificationMethod', 'DidService', 'DidResolutionCache', 'GnapGrant', 'GnapContinuation', 'GnapClientInstance', 'GnapInteraction']
