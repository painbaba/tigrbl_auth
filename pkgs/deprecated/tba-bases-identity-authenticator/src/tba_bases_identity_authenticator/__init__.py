"""Compatibility facade for :mod:`tba_bases_authenticator`."""

import warnings as _warnings

_warnings.warn(
    "tba-bases-identity-authenticator is deprecated; install tba-bases-authenticator and import tba_bases_authenticator instead.",
    DeprecationWarning,
    stacklevel=2,
)


from tba_bases_authenticator import *  # noqa: F401,F403
from tba_bases_authenticator import __all__ as _canonical_all


class WebAuthnAssertionMixin:
    """Removed compatibility shell; use PublicKeyAssertionVerificationBase."""

    async def verify_webauthn_assertion(self, assertion, credential):
        raise NotImplementedError(
            "use tba-bases-public-key-authentication"
        )


__all__ = [*_canonical_all, "WebAuthnAssertionMixin"]
