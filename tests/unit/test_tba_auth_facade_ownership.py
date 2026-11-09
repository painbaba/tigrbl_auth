from __future__ import annotations

import hashlib
import importlib
import pytest
import sys
from contextlib import contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PKGS = ROOT / "pkgs"
LARGE_FILE_THRESHOLD = 400


def package_root(name: str) -> Path:
    matches = sorted(PKGS.glob(f"**/{name}/pyproject.toml"))
    assert matches, f"missing package root for {name}"
    return matches[0].parent


def package_src_roots() -> list[Path]:
    return sorted(PKGS.glob("**/src"))


FACADE_PACKAGE = package_root("tba-auth")
FACADE_ROOT = FACADE_PACKAGE / "src" / "tba_auth"


SPLIT_MODULE_PREFIXES = (
    "tba_protocol_",
    "tba_authn_",
    "tba_authorization_",
    "tba_identity_",
    "tba_certification_release",
)
TABLE_MODULE_PREFIXES = ("tba_storage_core",)


FACADE_MODULES = {
    "tba_auth.config.deployment": "tba_runtime_identity.deployment",
    "tba_auth.config.surfaces": "tba_runtime_identity.surfaces",
    "tba_auth.errors": "tba_primitives_identity.errors",
    "tba_auth.jwtoken": "tba_protocol_oauth.jwtoken",
    "tba_auth.oidc_id_token": "tba_protocol_oidc.id_token",
    "tba_auth.oidc_userinfo": "tba_server_identity.userinfo_runtime",
    "tba_auth.rfc.rfc8693": "tba_protocol_oauth.standards.token_exchange",
    "tba_auth.rfc.rfc7519": "tba_protocol_oauth.standards.json_web_token",
    "tba_auth.rfc.rfc8725": "tba_protocol_oauth.standards.jwt_best_practices",
    "tba_auth.rfc.rfc7517": "tba_provider_identity_jose.standards.rfc7517",
    "tba_auth.rfc.rfc7518": "tba_provider_identity_jose.standards.rfc7518",
    "tba_auth.security.admin_gate": "tba_router_administration_gate",
    "tba_auth.security.certification": "tba_certification_release.certification",
    "tba_auth.security.runtime_metadata": "tba_certification_release.runtime_metadata",
    "tba_auth.services.advanced_identity_plane": "tba_runtime_identity_administration.advanced_identity_plane",
    "tba_auth.services.governance_extension_plane": "tba_runtime_authorization_policy.governance_extension",
    "tba_auth.services.policy_invariants": "tba_runtime_authorization_policy",
    "tba_auth.services.policy_control_plane": "tba_runtime_authorization_policy.control_plane",
    "tba_auth.services.tenant_discovery": "tba_protocol_oidc.tenant_discovery",
    "tba_auth.standards.jose.rfc7515": "tba_provider_identity_jose.standards.rfc7515",
    "tba_auth.standards.jose.rfc7517": "tba_provider_identity_jose.standards.rfc7517",
    "tba_auth.standards.jose.rfc7518": "tba_provider_identity_jose.standards.rfc7518",
    "tba_auth.standards.oauth2.dpop": "tba_protocol_oauth.standards.dpop",
    "tba_auth.standards.oauth2.rfc9700": "tba_protocol_oauth.standards.oauth_security_bcp",
    "tba_auth.standards.oauth2.resource_verifier_contract": "tba_protocol_oauth.standards.resource_verifier_contract",
    "tba_auth.standards.oauth2.token_exchange": "tba_server_identity.token_exchange_runtime",
    "tba_auth.standards.oidc.userinfo": "tba_server_identity.userinfo_runtime",
    "tba_auth.services.release_posture_plane": "tba_certification_release.release_posture",
    "tba_auth.services.session_service": "tba_runtime_identity_storage.session_service",
    "tba_auth.services.token_service": "tba_runtime_identity.token_service",
    "tba_auth.release_signing": "tba_runtime_identity_authoring.release_signing",
    "tba_auth.services.authorization_provenance": "tba_runtime_authorization_policy.provenance",
    "tba_auth.uix.admin_console": "tba_operator_identity.uix.admin_console",
    "tba_auth.db": "tba_runtime_identity_storage.engine",
    "tba_auth.tables": "tba_storage_core.tables",
    "tba_auth.migrations": "tba_runtime_identity_storage.migrations",
    "tba_auth.migrations.helpers": "tba_storage_core.migrations.helpers",
    "tba_auth.migrations.runtime": "tba_runtime_identity_storage.migrations.runtime",
}

EXECUTABLE_FACADE_MODULES: dict[str, str] = {
    "tba_auth.standards.oauth2.introspection": (
        "compatibility composition over layer 30, 50, 60, and 80 owners"
    ),
}

INSTALLED_FACADE_MODULES = {
    key: FACADE_MODULES[key]
    for key in (
        "tba_auth.config.deployment",
        "tba_auth.config.surfaces",
        "tba_auth.errors",
        "tba_auth.jwtoken",
        "tba_auth.oidc_id_token",
        "tba_auth.security.admin_gate",
        "tba_auth.security.certification",
        "tba_auth.security.runtime_metadata",
        "tba_auth.services.governance_extension_plane",
        "tba_auth.services.policy_invariants",
        "tba_auth.services.policy_control_plane",
        "tba_auth.services.tenant_discovery",
        "tba_auth.release_signing",
        "tba_auth.services.authorization_provenance",
        "tba_auth.standards.jose.rfc7515",
        "tba_auth.standards.jose.rfc7517",
        "tba_auth.standards.jose.rfc7518",
        "tba_auth.standards.oauth2.resource_verifier_contract",
        "tba_auth.db",
        "tba_auth.tables",
        "tba_auth.migrations",
        "tba_auth.migrations.helpers",
        "tba_auth.migrations.runtime",
    )
}


@contextmanager
def source_tree_paths_first():
    original_path = list(sys.path)
    removed_modules = {
        name: module
        for name, module in sys.modules.items()
        if (
            name == "tba_auth"
            or name.startswith("tba_auth.")
            or name.startswith(SPLIT_MODULE_PREFIXES)
        )
        and not name.startswith(TABLE_MODULE_PREFIXES)
    }
    for name in list(removed_modules):
        sys.modules.pop(name, None)
    try:
        root_value = str(ROOT)
        sys.path = [value for value in sys.path if value not in {root_value, ""}]
        for src in package_src_roots():
            value = str(src)
            if value not in sys.path:
                sys.path.insert(0, value)
        yield
    finally:
        for name in list(sys.modules):
            if (
                name == "tba_auth"
                or name.startswith("tba_auth.")
                or (
                    name.startswith(SPLIT_MODULE_PREFIXES)
                    and not name.startswith(TABLE_MODULE_PREFIXES)
                )
            ):
                sys.modules.pop(name, None)
        sys.modules.update(removed_modules)
        sys.path = original_path


@contextmanager
def package_src_paths_only():
    original_path = list(sys.path)
    removed_modules = {
        name: module
        for name, module in sys.modules.items()
        if (
            name == "tba_auth"
            or name.startswith("tba_auth.")
            or name.startswith(SPLIT_MODULE_PREFIXES)
        )
        and not name.startswith(TABLE_MODULE_PREFIXES)
    }
    for name in list(removed_modules):
        sys.modules.pop(name, None)
    try:
        root_values = {str(ROOT), ""}
        sys.path = [value for value in sys.path if value not in root_values]
        for src in package_src_roots():
            value = str(src)
            if value not in sys.path:
                sys.path.insert(0, value)
        yield
    finally:
        for name in list(sys.modules):
            if (
                name == "tba_auth"
                or name.startswith("tba_auth.")
                or (
                    name.startswith(SPLIT_MODULE_PREFIXES)
                    and not name.startswith(TABLE_MODULE_PREFIXES)
                )
            ):
                sys.modules.pop(name, None)
        sys.modules.update(removed_modules)
        sys.path = original_path


def test_legacy_facade_modules_alias_canonical_module_objects() -> None:
    with source_tree_paths_first():
        for legacy_name, canonical_name in FACADE_MODULES.items():
            legacy = importlib.import_module(legacy_name)
            canonical = importlib.import_module(canonical_name)

            assert legacy is canonical


def test_only_cross_layer_introspection_compatibility_facade_remains() -> None:
    assert EXECUTABLE_FACADE_MODULES == {
        "tba_auth.standards.oauth2.introspection": (
            "compatibility composition over layer 30, 50, 60, and 80 owners"
        ),
    }


def test_legacy_facade_ops_are_not_supported() -> None:
    assert not (FACADE_ROOT / "ops").exists()


def test_legacy_framework_facade_is_not_supported() -> None:
    with package_src_paths_only():
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module("tba_auth.framework")


def test_pqc_touched_facades_do_not_own_runtime_implementation() -> None:
    facade_paths = [
        FACADE_ROOT / "jwtoken.py",
        FACADE_ROOT / "standards" / "jose" / "rfc7515.py",
        FACADE_ROOT / "standards" / "jose" / "rfc7517.py",
        FACADE_ROOT / "standards" / "jose" / "rfc7518.py",
        FACADE_ROOT / "standards" / "oauth2" / "resource_verifier_contract.py",
    ]
    forbidden_tokens = {
        "class JWTCoder",
        "def sign_jws",
        "def verify_jws",
        "def load_pqc",
        "ML_DSA_65_ALG =",
        "sign_pqc_payload",
        "verify_pqc_signature",
        "pqcrypto",
        "ProtectedResourceVerifierContract:",
    }

    for path in facade_paths:
        source = path.read_text(encoding="utf-8")
        assert "alias_module" in source, path.relative_to(ROOT).as_posix()
        for token in forbidden_tokens:
            assert token not in source, f"{path.relative_to(ROOT).as_posix()} owns {token}"


def test_installable_tba_auth_facade_exposes_runtime_legacy_paths() -> None:
    with package_src_paths_only():
        for legacy_name, canonical_name in INSTALLED_FACADE_MODULES.items():
            legacy = importlib.import_module(legacy_name)
            canonical = importlib.import_module(canonical_name)

            assert legacy is canonical


def test_installable_tba_auth_facade_exposes_runtime_package() -> None:
    with package_src_paths_only():
        legacy = importlib.import_module("tba_auth.runtime")
        canonical = importlib.import_module("tba_runtime_identity")

        assert legacy is canonical
        assert legacy.LazyASGIApplication is canonical.LazyASGIApplication


def test_installable_tba_auth_facade_exposes_storage_legacy_submodules() -> None:
    with package_src_paths_only():
        legacy_user = importlib.import_module("tba_auth.tables.user")
        canonical_user = importlib.import_module("tba_storage_core.tables.user")
        legacy_engine = importlib.import_module("tba_auth.tables.engine")
        canonical_engine = importlib.import_module("tba_runtime_identity_storage.engine")
        legacy_revision = importlib.import_module(
            "tba_auth.migrations.versions.0011_delegation_grant_lifecycle_tables"
        )
        canonical_revision = importlib.import_module(
            "tba_storage_core.migrations.versions.0011_delegation_grant_lifecycle_tables"
        )

        assert legacy_user is canonical_user
        assert legacy_user.User is canonical_user.User
        assert legacy_engine is canonical_engine
        assert legacy_engine.get_db is canonical_engine.get_db
        assert legacy_revision is canonical_revision
        assert legacy_revision.revision == canonical_revision.revision


def test_installable_tba_auth_facade_exposes_rfc_legacy_modules() -> None:
    facade_modules = {
        "tba_auth.rfc.rfc7636_pkce": (
            "tba_protocol_oauth.standards.proof_key_for_code_exchange"
        ),
        "tba_auth.rfc.rfc7662_introspection": (
            "tba_protocol_oauth.standards.introspection"
        ),
        "tba_auth.rfc.rfc9449_dpop": (
            "tba_protocol_oauth.standards.dpop"
        ),
        "tba_auth.rfc.rfc7515": "tba_provider_identity_jose.standards.rfc7515",
        "tba_auth.rfc.rfc7516": "tba_provider_identity_jose.standards.rfc7516",
        "tba_auth.rfc.rfc7519": "tba_protocol_oauth.standards.json_web_token",
        "tba_auth.rfc.rfc7520": "tba_provider_identity_jose.standards.rfc7520",
        "tba_auth.rfc.rfc8725": "tba_protocol_oauth.standards.jwt_best_practices",
        "tba_auth.rfc.rfc8812": "tba_provider_identity_jose.standards.rfc8812",
    }

    with package_src_paths_only():
        for legacy_name, canonical_name in facade_modules.items():
            legacy = importlib.import_module(legacy_name)
            canonical = importlib.import_module(canonical_name)

            assert legacy is canonical
        rfc8414 = importlib.import_module("tba_auth.rfc.rfc8414")
        assert not hasattr(rfc8414, "include_rfc8414")
        carrier = importlib.import_module(
            "tba_app_backend_core.surfaces.authorization_server_metadata_surface"
        )
        assert carrier.include_rfc8414.__module__ == carrier.__name__


def test_rfc8785_core_legacy_warns_and_facade_module_is_removed() -> None:
    with package_src_paths_only():
        canonical = importlib.import_module("tba_primitives_identity.json_canonicalization")

        sys.modules.pop("tba_primitives_identity.rfc8785", None)
        with pytest.warns(
            DeprecationWarning,
            match="tba_codec_jcs",
        ):
            core_legacy = importlib.import_module("tba_primitives_identity.rfc8785")

        sys.modules.pop("tba_auth.rfc.rfc8785", None)
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module("tba_auth.rfc.rfc8785")

        identity = importlib.import_module("tba_primitives_identity")
        assert identity.canonicalize is core_legacy.canonicalize is canonical.canonicalize
        assert core_legacy.canonicalize_json is canonical.canonicalize_json

        # Preserve the legacy serialization and warn at the call site.
        with pytest.warns(DeprecationWarning, match="tba_codec_jcs") as warnings:
            assert identity.canonicalize({"n": 1e-6}) == b'{"n":1e-6}'
            assert core_legacy.canonicalize_json('{"n": 0.000001}') == b'{"n":1e-6}'
        assert len(warnings) == 2
        assert all(warning.filename == __file__ for warning in warnings)


def test_installable_tba_auth_facade_does_not_advertise_root_only_rfc_symbols() -> None:
    with package_src_paths_only():
        package = importlib.import_module("tba_auth")

        assert "RFC8932_SPEC_URL" not in dir(package)
        assert "enforce_encrypted_dns" not in dir(package)


def test_installable_resource_validation_api_imports_facade_metadata_modules() -> None:
    with package_src_paths_only():
        metadata = importlib.import_module(
            "tba_auth.standards.oauth2.resource_validation_metadata"
        )
        contract = importlib.import_module(
            "tba_auth.standards.oauth2.resource_verifier_contract"
        )
        package = importlib.import_module("tba_app_backend_resource_validation")

        assert metadata.CAPABILITIES_METADATA_PATH == "/metadata/capabilities"
        from tba_runtime_identity.deployment import resolve_deployment

        assert contract.build_protected_resource_verifier_contract(
            deployment=resolve_deployment()
        ).fail_closed is True
        assert package.PRODUCT_SURFACE == "resource-validation-app"


def test_tba_auth_facade_declares_canonical_runtime_dependencies() -> None:
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomli as tomllib

    metadata = tomllib.loads(
        (FACADE_PACKAGE / "pyproject.toml").read_text(encoding="utf-8")
    )

    assert set(metadata["project"]["dependencies"]).issuperset(
        {
            "tba-cli-identity==0.4.0.dev2",
            "tba-runtime-identity-administration==0.4.0.dev2",
            "tba-runtime-identity-authoring==0.4.0.dev2",
            "tba-credentials==0.4.0.dev2",
            "tba-provider-identity-jose==0.4.0.dev2",
            "tba-protocol-oauth==0.4.0.dev2",
            "tba-operator-identity==0.4.0.dev2",
            "tba-concrete-authority-graph==0.4.0.dev2",
            "tba-concrete-authorization-policy-attributes-mapping==0.4.0.dev2",
            "tba-concrete-authorization-policy-combiner-default==0.4.0.dev2",
            "tba-concrete-authorization-policy-evaluators-default==0.4.0.dev2",
            "tba-concrete-authorization-policy-obligations==0.4.0.dev2",
            "tba-concrete-authorization-policy-rules==0.4.0.dev2",
            "tba-provider-security-authorization-provenance-builder==0.1.0",
            "tba-runtime-authorization-policy==0.4.0.dev2",
            "tba-certification-release==0.4.0.dev2",
            "tba-runtime-identity==0.4.0.dev2",
            "tba-server-identity==0.4.0.dev2",
            "tba-storage-core==0.4.0.dev2",
            "tba-runtime-identity-storage==0.4.0.dev2",
        }
    )


def test_jose_no_longer_owns_protocol_jwt_facades() -> None:
    jose_root = package_root("tba-provider-identity-jose") / "src" / "tba_provider_identity_jose"
    oauth_root = package_root("tba-protocol-oauth") / "src" / "tba_protocol_oauth"
    oidc_root = package_root("tba-protocol-oidc") / "src" / "tba_protocol_oidc"

    assert not (jose_root / "jwtoken.py").exists()
    assert not (jose_root / "jwks_service.py").exists()
    assert not (jose_root / "standards" / "rfc7519.py").exists()
    assert not (jose_root / "standards" / "rfc8725.py").exists()
    assert (oauth_root / "jwtoken.py").exists()
    assert (oauth_root / "standards" / "json_web_token.py").exists()
    assert (oauth_root / "standards" / "jwt_best_practices.py").exists()
    assert (oidc_root / "jwks_service.py").exists()


def test_oauth_standards_use_descriptive_module_names() -> None:
    oauth_standards = (
        package_root("tba-protocol-oauth")
        / "src"
        / "tba_protocol_oauth"
        / "standards"
    )

    descriptive_modules = {
        "bearer_token_usage.py",
        "json_web_token.py",
        "revocation.py",
        "assertion_framework.py",
        "jwt_client_auth.py",
        "dynamic_client_registration.py",
        "client_registration_management.py",
        "authorization_framework.py",
        "token_endpoint.py",
        "proof_key_for_code_exchange.py",
        "introspection.py",
        "native_apps.py",
        "authorization_server_metadata.py",
        "authorization_server_metadata_endpoint.py",
        "legacy_jwt_client_assertions.py",
        "device_authorization.py",
        "token_exchange.py",
        "mutual_tls_client_authentication.py",
        "resource_indicators.py",
        "jwt_best_practices.py",
        "jwt_access_tokens.py",
        "jwt_secured_authorization_requests.py",
        "pushed_authorization_requests.py",
        "issuer_identification.py",
        "rich_authorization_requests.py",
        "oauth_security_bcp.py",
        "protected_resource_metadata.py",
    }
    removed_rfc_modules = {
        "rfc6750.py",
        "rfc7009.py",
        "rfc7519.py",
        "rfc7521.py",
        "rfc7523.py",
        "rfc7591.py",
        "rfc7592.py",
        "rfc6749.py",
        "rfc6749_token.py",
        "rfc7636_pkce.py",
        "rfc9449_dpop.py",
        "rfc7662.py",
        "rfc7662_introspection.py",
        "rfc8252.py",
        "rfc8414.py",
        "rfc8414_metadata.py",
        "rfc8523.py",
        "rfc8628.py",
        "rfc8693.py",
        "rfc8705.py",
        "rfc8707.py",
        "rfc8725.py",
        "rfc9068.py",
        "rfc9101.py",
        "rfc9126.py",
        "rfc9207.py",
        "rfc9396.py",
        "rfc9700.py",
        "rfc9728.py",
    }

    for filename in descriptive_modules:
        assert (oauth_standards / filename).exists()
    for filename in removed_rfc_modules:
        assert not (oauth_standards / filename).exists()


def test_tba_auth_has_no_large_exact_copies_of_split_package_modules() -> None:
    canonical_hashes: dict[str, list[Path]] = {}
    for package_root in package_src_roots():
        if package_root.parent.name == "tba-auth":
            continue
        for path in package_root.rglob("*.py"):
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            canonical_hashes.setdefault(digest, []).append(path)

    duplicate_large_files: list[str] = []
    for path in sorted(FACADE_ROOT.rglob("*.py")):
        if len(path.read_text(encoding="utf-8").splitlines()) <= LARGE_FILE_THRESHOLD:
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        matches = canonical_hashes.get(digest, [])
        if matches:
            duplicate_large_files.append(
                f"{path.relative_to(ROOT).as_posix()} duplicates "
                f"{matches[0].relative_to(ROOT).as_posix()}"
            )

    assert duplicate_large_files == []
