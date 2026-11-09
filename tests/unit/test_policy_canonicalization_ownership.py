from __future__ import annotations

import ast
from hashlib import sha256
from pathlib import Path

from tba_runtime_authorization_policy import assurance, provenance
from tba_primitives_identity.json_canonicalization import canonical_hash, canonical_json


ROOT = Path(__file__).resolve().parents[2]


def test_policy_canonicalization_helpers_are_owned_by_identity_core() -> None:
    assert provenance.canonical_json is canonical_json
    assert provenance.canonical_hash is canonical_hash
    assert assurance.canonical_json is canonical_json
    assert assurance.canonical_hash is canonical_hash
    assert canonical_json({"b": 2, "a": 1}) == '{"a":1,"b":2}'
    assert canonical_json({"values": ("z", "a")}) == '{"values":["z","a"]}'
    assert canonical_json({"values": {"z", "a"}}) == '{"values":["a","z"]}'
    expected = sha256(br'{"amount":1e-06,"label":"\u00e9"}').hexdigest()
    payload = {"amount": 1e-6, "label": "é"}
    assert provenance.canonical_hash(payload) == assurance.canonical_hash(payload) == expected


def test_policy_provenance_builders_are_concrete_backed() -> None:
    assert provenance.build_authorization_decision_trace.__module__ == (
        "tba_concrete_authorization_provenance"
    )
    assert provenance.build_delegation_provenance.__module__ == (
        "tba_concrete_authorization_provenance"
    )


def test_authz_policy_no_longer_defines_canonicalization_helpers() -> None:
    helper_names = {"_normalize", "canonical_json", "canonical_hash"}
    for relative_path in (
        "pkgs/60-runtime/tba-runtime-authorization-policy/src/tba_runtime_authorization_policy/provenance.py",
        "pkgs/60-runtime/tba-runtime-authorization-policy/src/tba_runtime_authorization_policy/assurance.py",
    ):
        tree = ast.parse((ROOT / relative_path).read_text(encoding="utf-8"))
        defined = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        assert not (defined & helper_names), relative_path
