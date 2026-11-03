import hashlib

import cbor2
import pytest

from tba_concrete_claim_authorization_context import AuthorizationContextClaim
from tba_concrete_claim_access_token_digest import AccessTokenDigestClaim
from tba_concrete_claim_authentication_context import AuthenticationContextClaim


def test_cbor_roundtrip():
    context = AuthorizationContextClaim({"type": "moqt", "action": "SUBSCRIBE"})
    digest = hashlib.sha256(b"access-token").digest()
    ath = AccessTokenDigestClaim.from_cwt_value(digest)
    payload = {"actx": context.to_cwt_value(field_labels={"action": 1}),
               "ath": ath.to_cwt_value(), 6: 1234, 7: b"proof-id"}
    decoded = cbor2.loads(cbor2.dumps(payload, canonical=True))
    assert decoded == {"actx": {0: "moqt", 1: "SUBSCRIBE"},
                       "ath": digest, 6: 1234, 7: b"proof-id"}
    assert AccessTokenDigestClaim.from_cwt_value(decoded["ath"]).value == ath.value
    assert AuthenticationContextClaim("urn:example:assurance:high").name == "acr"


@pytest.mark.parametrize("value", [None, "acr", {}, {"type": ""}, {"type": 1}, {0: "moqt"}])
def test_invalid_context(value):
    with pytest.raises(ValueError):
        AuthorizationContextClaim(value)


@pytest.mark.parametrize("labels", [{}, {"action": 0}, {"type": 3},
                                    {"action": True}, {"action": 1, "other": 1}])
def test_invalid_context_labels(labels):
    with pytest.raises(ValueError):
        AuthorizationContextClaim({"type": "moqt", "action": "SUBSCRIBE"}).to_cwt_value(field_labels=labels)


@pytest.mark.parametrize("value", [b"short", "x" * 32, None])
def test_invalid_cwt_digest(value):
    with pytest.raises(ValueError):
        AccessTokenDigestClaim.from_cwt_value(value)


@pytest.mark.parametrize("value", ["short", "!" * 43, "a" * 44, "\u00e9"])
def test_invalid_text_digest_conversion(value):
    with pytest.raises(ValueError):
        AccessTokenDigestClaim(value).to_cwt_value()
