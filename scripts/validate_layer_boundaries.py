"""Validate first-party package dependency and source-layer boundaries.

The package directory is the authoritative layer declaration.  This module is
kept dependency-free so it can run before the workspace itself is installed.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 CI
    import tomli as tomllib  # type: ignore[no-redef]

try:
    from scripts.package_layer_policy import (
        classify_layer,
        dependency_allowed,
        load_layer_policy,
        package_dependency_allowed,
    )
except ModuleNotFoundError:  # direct script execution
    from package_layer_policy import (
        classify_layer,
        dependency_allowed,
        load_layer_policy,
        package_dependency_allowed,
    )


ROOT = Path(__file__).resolve().parents[1]
PKGS = ROOT / "pkgs"

LAYER_POLICY = load_layer_policy(PKGS / "layers.toml")
LAYER_ORDER = LAYER_POLICY.layer_ids
NON_PRODUCTION_LAYERS = LAYER_POLICY.terminal_layers
ROUTER_LAYER = "80-routers"
BACKEND_APP_LAYER = "90-backend-apps"
EXAMPLE_LAYER = "110-examples"
TEST_LAYER = "120-tests"

# Capabilities orchestrate implemented behavior.  Contract value types and
# ports and primitive value helpers remain valid vocabulary, but capability
# implementations may not reach into storage tables or implementation bases. In
# particular,
# layer 40 never *implements* a layer-02/05 abstraction; implementation starts
# in layer 10 and concrete integrations belong in layer 20.
CAPABILITY_ALLOWED_LAYERS = frozenset(
    {
        "00-primitives",
        "02-contracts",
        "10-concrete",
        "20-providers",
        "30-storage-runtime",
        "40-capabilities",
    }
)
CAPABILITY_FORBIDDEN_LAYERS = frozenset({"01-storage", "05-bases"})
CAPABILITY_FORBIDDEN_BASE_LAYERS = frozenset(
    {"00-primitives", "01-storage", "02-contracts", "05-bases"}
)
CAPABILITY_IMPLEMENTATION_ROOTS = frozenset(
    {"tba_concrete_capability", "tba_concrete_capability_default"}
)

# Compatibility aggregators preserve old imports for one release. They do not
# own capability implementations and are excluded from the one-owner rule.
CAPABILITY_COMPATIBILITY_AGGREGATORS = frozenset({})

# Layer 40 is intentionally sparse and opt-in.  Each entry names the complete
# use case that would disappear if the orchestration package were removed.
CAPABILITY_PURPOSES = {
    "tba-capability-communications-identity": (
        "Compose domain assessment and recheck with injected protocol checks and audit writing."
    ),
    "tba-capability-adaptive-authentication": (
        "coordinate a normalized adaptive-authentication decision"
    ),
    "tba-capability-administrative-resource": (
        "coordinate generic administrative-resource lifecycle operations"
    ),
    "tba-capability-access-governance": (
        "coordinate entitlement management, provisioning, and access reviews"
    ),
    "tba-capability-account-self-service": (
        "coordinate authenticated profile, password, session, and consent lifecycle"
    ),
    "tba-capability-attestation-appraisal": (
        "coordinate evidence appraisal and result recording"
    ),
    "tba-capability-api-key-authentication": (
        "coordinate user API-key verification with durable credential operations"
    ),
    "tba-capability-authenticator-attestation": (
        "coordinate attestation format verification, metadata resolution, trust appraisal, and reappraisal"
    ),
    "tba-capability-client-registration": (
        "coordinate client and registration metadata lifecycle with optional "
        "audit recording"
    ),
    "tba-capability-client-secret-authentication": (
        "coordinate client-secret verification with client lookup"
    ),
    "tba-capability-digital-credential-issuance": (
        "coordinate credential configuration, wallet trust, offers, and issuance"
    ),
    "tba-capability-digital-credential-presentation": (
        "coordinate holder consent, replay defense, and presentation verification"
    ),
    "tba-capability-identity-document": (
        "coordinate identity-document parsing, resolution, and verification through injected implementations"
    ),
    "tba-capability-possession-proof": (
        "coordinate proof verification with replay acceptance and holder-binding evaluation"
    ),
    "tba-capability-protected-envelope": (
        "coordinate protected-envelope issuance and verification through injected cryptographic implementations"
    ),
    "tba-capability-workload-credential-brokering": (
        "coordinate delegated workload reference resolution, authorization, credential delivery, and trust material"
    ),
    "tba-capability-identity-administration": (
        "coordinate identity lifecycle administration"
    ),
    "tba-capability-key-administration": (
        "coordinate key rotation and publication through injected implementations"
    ),
    "tba-capability-mfa-challenge": (
        "coordinate begin and complete operations for an MFA challenge"
    ),
    "tba-capability-operator-administration": (
        "coordinate policy-gated operator administration"
    ),
    "tba-capability-password-authentication": (
        "coordinate password verification with identity lookup"
    ),
    "tba-capability-delegated-access-negotiation": (
        "coordinate negotiated grant requests, continuation, and token rotation"
    ),
    "tba-capability-artifact-processing": (
        "coordinate protocol-neutral artifact decoding, validation, encoding, "
        "and error normalization through replaceable processors"
    ),
    "tba-capability-policy-evaluation": (
        "coordinate normalized policy evaluation, batch evaluation, entity search, "
        "and service description"
    ),
    "tba-capability-policy-administration": (
        "coordinate RBAC, ABAC, delegated-administration, and policy simulation operations"
    ),
    "tba-capability-policy-assurance": (
        "coordinate authorization invariants, replay checks, and assurance reporting"
    ),
    "tba-capability-authorization-request-staging": (
        "coordinate durable pushed-request creation with optional audit recording"
    ),
    "tba-capability-protected-resource-authorization": (
        "coordinate normalized protected-resource token and claims authorization"
    ),
    "tba-capability-public-key-authentication": (
        "coordinate durable ceremony consumption, credential resolution, assertion verification, and session evidence"
    ),
    "tba-capability-public-key-credential-management": (
        "coordinate authenticated listing, naming, and revocation of registered public-key credentials"
    ),
    "tba-capability-public-key-registration": (
        "coordinate durable ceremony reservation, attestation verification, credential insertion, and audit evidence"
    ),
    "tba-capability-replay-protection": (
        "coordinate normalized replay reservations across protocol mappings, "
        "durable repositories, and replaceable providers"
    ),
    "tba-capability-realm-administration": (
        "coordinate realm lifecycle administration"
    ),
    "tba-capability-security-event-delivery": (
        "coordinate security-event transmission, receipt, and recording"
    ),
    "tba-capability-service-key-authentication": (
        "coordinate service-key verification with durable credential operations"
    ),
    "tba-capability-tenant-administration": (
        "coordinate tenant lifecycle administration"
    ),
    "tba-capability-token-introspection": (
        "coordinate protocol-neutral token-state lookup and profile validation"
    ),
    "tba-capability-token-issuance": (
        "coordinate token-pair issuance and refresh rotation across signing and "
        "durable lifecycle operations"
    ),
    "tba-capability-token-exchange": (
        "coordinate normalized security-token exchange across verification, "
        "issuance, durable lineage, and audit operations"
    ),
    "tba-capability-token-revocation": (
        "coordinate durable token revocation with optional audit recording"
    ),
    "tba-capability-workload-identity": (
        "coordinate workload credential retrieval and identity verification"
    ),
}

REQ_NAME_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)")
DYNAMIC_IMPORT_RE = re.compile(
    r"(?:import_module|find_spec)\(\s*['\"](?P<module>[A-Za-z0-9_.]+)['\"]"
)


@dataclass(frozen=True)
class Package:
    distribution: str
    import_roots: tuple[str, ...]
    layer: str
    path: Path
    dependencies: tuple[str, ...]


@dataclass(frozen=True)
class Violation:
    kind: str
    package: str
    package_layer: str
    target: str
    target_layer: str
    path: str
    line: int | None
    detail: str


def _normalize_distribution(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _dependency_name(requirement: object) -> str | None:
    match = REQ_NAME_RE.match(str(requirement))
    return _normalize_distribution(match.group(1)) if match else None


def _terminal_dependency_forbidden(consumer_layer: str, target_layer: str) -> bool:
    return not dependency_allowed(consumer_layer, target_layer, LAYER_POLICY)


def _manifest_dependencies(data: dict[str, object]) -> set[str]:
    project = data.get("project", {})
    if not isinstance(project, dict):
        project = {}
    requirements: list[object] = list(project.get("dependencies", []) or [])
    optional = project.get("optional-dependencies", {}) or {}
    if isinstance(optional, dict):
        for group in optional.values():
            if isinstance(group, list):
                requirements.extend(group)

    dependency_groups = data.get("dependency-groups", {}) or {}
    if isinstance(dependency_groups, dict):
        for group in dependency_groups.values():
            if isinstance(group, list):
                requirements.extend(group)

    tool = data.get("tool", {}) or {}
    if isinstance(tool, dict):
        poetry = tool.get("poetry", {}) or {}
        if isinstance(poetry, dict):
            for table_name in ("dependencies", "dev-dependencies"):
                table = poetry.get(table_name, {}) or {}
                if isinstance(table, dict):
                    requirements.extend(table)
            groups = poetry.get("group", {}) or {}
            if isinstance(groups, dict):
                for group in groups.values():
                    if isinstance(group, dict):
                        table = group.get("dependencies", {}) or {}
                        if isinstance(table, dict):
                            requirements.extend(table)

    return {name for item in requirements if (name := _dependency_name(item))}


def discover_packages(root: Path = ROOT) -> tuple[Package, ...]:
    packages: list[Package] = []
    seen_distributions: dict[str, Path] = {}
    seen_import_roots: dict[str, Path] = {}
    pkgs = root / "pkgs"

    for manifest in sorted(pkgs.rglob("pyproject.toml")):
        layer = classify_layer(manifest.parent, LAYER_POLICY, pkgs)
        data = tomllib.loads(manifest.read_text(encoding="utf-8"))
        project = data.get("project", {})
        if not isinstance(project, dict) or not project.get("name"):
            raise ValueError(f"missing project.name: {manifest}")
        distribution = _normalize_distribution(str(project["name"]))
        if previous := seen_distributions.get(distribution):
            raise ValueError(
                f"duplicate distribution {distribution!r}: {previous} and {manifest}"
            )
        seen_distributions[distribution] = manifest

        src = manifest.parent / "src"
        import_roots = (
            tuple(
                sorted(
                    child.name
                    for child in src.iterdir()
                    if src.is_dir()
                    and child.is_dir()
                    and not child.name.endswith((".dist-info", ".egg-info"))
                    and child.name != "__pycache__"
                )
            )
            if src.is_dir()
            else ()
        )
        for import_root in import_roots:
            if previous := seen_import_roots.get(import_root):
                raise ValueError(
                    f"duplicate import root {import_root!r}: {previous} and {manifest}"
                )
            seen_import_roots[import_root] = manifest

        packages.append(
            Package(
                distribution=distribution,
                import_roots=import_roots,
                layer=layer,
                path=manifest.parent,
                dependencies=tuple(sorted(_manifest_dependencies(data))),
            )
        )
    return tuple(packages)


def _base_root(base: ast.expr, imports: dict[str, str]) -> str | None:
    node = base
    while isinstance(node, (ast.Subscript, ast.Call)):
        node = node.value if isinstance(node, ast.Subscript) else node.func
    while isinstance(node, ast.Attribute):
        node = node.value
    if isinstance(node, ast.Name):
        return imports.get(node.id)
    return None


def validate(root: Path = ROOT) -> tuple[Violation, ...]:
    packages = discover_packages(root)
    by_distribution = {item.distribution: item for item in packages}
    by_import_root = {
        import_root: item for item in packages for import_root in item.import_roots
    }
    violations: list[Violation] = []

    for package in packages:
        if package.layer == ROUTER_LAYER and not package.distribution.startswith(
            "tba-router-"
        ):
            violations.append(
                Violation(
                    kind="router-package-name",
                    package=package.distribution,
                    package_layer=package.layer,
                    target="tba-router-*",
                    target_layer=ROUTER_LAYER,
                    path=package.path.relative_to(root).as_posix(),
                    line=None,
                    detail="layer-80 packages use the router distribution family",
                )
            )
        if package.layer == BACKEND_APP_LAYER and not package.distribution.startswith(
            "tba-app-backend-"
        ):
            violations.append(
                Violation(
                    kind="backend-app-package-name",
                    package=package.distribution,
                    package_layer=package.layer,
                    target="tba-app-backend-*",
                    target_layer=BACKEND_APP_LAYER,
                    path=package.path.relative_to(root).as_posix(),
                    line=None,
                    detail="layer-90 backend packages use the backend-app distribution family",
                )
            )

        for dependency in package.dependencies:
            target = by_distribution.get(dependency)
            if (
                package.layer == ROUTER_LAYER
                and target is not None
                and target.layer == BACKEND_APP_LAYER
            ):
                violations.append(
                    Violation(
                        kind="router-depends-on-backend-app",
                        package=package.distribution,
                        package_layer=package.layer,
                        target=target.distribution,
                        target_layer=target.layer,
                        path=(package.path / "pyproject.toml")
                        .relative_to(root)
                        .as_posix(),
                        line=None,
                        detail="routers are reusable dependencies of apps, never app consumers",
                    )
                )

    # Apply the canonical policy to every first-party manifest and source import.
    # Package-scoped exceptions are finite migration entries in pkgs/layers.toml.
    observed_edges: set[tuple[str, str]] = set()
    for package in packages:
        manifest = package.path / "pyproject.toml"
        for dependency in package.dependencies:
            target = by_distribution.get(dependency)
            if target is not None:
                observed_edges.add((package.distribution, target.distribution))
            if target is None or package_dependency_allowed(
                package.distribution,
                package.layer,
                target.distribution,
                target.layer,
                LAYER_POLICY,
            ):
                continue
            if package.layer == ROUTER_LAYER and target.layer == BACKEND_APP_LAYER:
                kind = "router-depends-on-backend-app"
                detail = (
                    "routers are reusable dependencies of apps, never app consumers"
                )
            elif target.layer in NON_PRODUCTION_LAYERS:
                kind = "terminal-layer-dependency"
                detail = "production cannot consume terminal packages; examples cannot consume tests"
            else:
                kind = "forbidden-layer-dependency"
                detail = "target layer is not allowed by pkgs/layers.toml"
            violations.append(
                Violation(
                    kind=kind,
                    package=package.distribution,
                    package_layer=package.layer,
                    target=target.distribution,
                    target_layer=target.layer,
                    path=manifest.relative_to(root).as_posix(),
                    line=None,
                    detail=detail,
                )
            )

        for source in sorted((package.path / "src").rglob("*.py")):
            text = source.read_text(encoding="utf-8-sig")
            tree = ast.parse(text, filename=str(source))
            imported_roots: set[tuple[str, int]] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported_roots.update(
                        (alias.name.split(".")[0], node.lineno) for alias in node.names
                    )
                elif (
                    isinstance(node, ast.ImportFrom) and node.level == 0 and node.module
                ):
                    imported_roots.add((node.module.split(".")[0], node.lineno))
            for match in DYNAMIC_IMPORT_RE.finditer(text):
                imported_roots.add(
                    (
                        match.group("module").split(".")[0],
                        text.count("\n", 0, match.start()) + 1,
                    )
                )

            relative_source = source.relative_to(root).as_posix()
            for import_root, line in sorted(imported_roots):
                target = by_import_root.get(import_root)
                if target is not None:
                    observed_edges.add((package.distribution, target.distribution))
                if target is None or package_dependency_allowed(
                    package.distribution,
                    package.layer,
                    target.distribution,
                    target.layer,
                    LAYER_POLICY,
                ):
                    continue
                if package.layer == ROUTER_LAYER and target.layer == BACKEND_APP_LAYER:
                    kind = "router-imports-backend-app"
                    detail = (
                        "routers are reusable dependencies of apps, never app consumers"
                    )
                elif target.layer in NON_PRODUCTION_LAYERS:
                    kind = "terminal-layer-import"
                    detail = "production cannot import terminal packages; examples cannot import tests"
                else:
                    kind = "forbidden-layer-import"
                    detail = f"first-party import root {import_root!r} crosses a forbidden layer edge"
                violations.append(
                    Violation(
                        kind=kind,
                        package=package.distribution,
                        package_layer=package.layer,
                        target=target.distribution,
                        target_layer=target.layer,
                        path=relative_source,
                        line=line,
                        detail=detail,
                    )
                )

    for consumer, target in sorted(LAYER_POLICY.exception_pairs):
        consumer_package = by_distribution.get(consumer)
        target_package = by_distribution.get(target)
        stale = (consumer, target) not in observed_edges
        if consumer_package is not None and target_package is not None:
            stale = stale or dependency_allowed(
                consumer_package.layer, target_package.layer, LAYER_POLICY
            )
        if not stale:
            continue
        violations.append(
            Violation(
                kind="stale-dependency-exception",
                package=consumer,
                package_layer=(
                    consumer_package.layer if consumer_package else "missing"
                ),
                target=target,
                target_layer=(target_package.layer if target_package else "missing"),
                path="pkgs/layers.toml",
                line=None,
                detail="remove migration exception that no longer covers a forbidden live edge",
            )
        )

    capability_packages = {
        item.distribution for item in packages if item.layer == "40-capabilities"
    }
    registry_path = root / "pkgs" / "40-capabilities" / "capability-families.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registered_packages = {
        str(item["package"]) for item in registry.get("capabilities", ())
    }
    if registered_packages != capability_packages:
        violations.append(
            Violation(
                kind="stale-capability-family-registry",
                package="40-capabilities",
                package_layer="40-capabilities",
                target="capability-families.json",
                target_layer="architecture-policy",
                path=registry_path.relative_to(root).as_posix(),
                line=None,
                detail="regenerate the registry after adding or removing a capability package",
            )
        )
    for package_name in sorted(capability_packages - set(CAPABILITY_PURPOSES)):
        package = by_distribution[package_name]
        violations.append(
            Violation(
                kind="unregistered-capability",
                package=package.distribution,
                package_layer=package.layer,
                target="capability-purpose-registry",
                target_layer="architecture-policy",
                path=package.path.relative_to(root).as_posix(),
                line=None,
                detail=(
                    "layer 40 is opt-in; document the multi-component use case or "
                    "move the implementation to its owning layer"
                ),
            )
        )
    for package_name in sorted(set(CAPABILITY_PURPOSES) - capability_packages):
        violations.append(
            Violation(
                kind="stale-capability-registration",
                package=package_name,
                package_layer="40-capabilities",
                target="capability-purpose-registry",
                target_layer="architecture-policy",
                path="scripts/validate_layer_boundaries.py",
                line=None,
                detail="registered layer-40 package does not exist",
            )
        )

    for package in packages:
        if package.layer != "40-capabilities":
            continue

        manifest = package.path / "pyproject.toml"
        has_capability_implementation = False
        capability_implementation_count = 0
        is_compatibility_aggregator = (
            package.distribution in CAPABILITY_COMPATIBILITY_AGGREGATORS
        )
        if (
            not is_compatibility_aggregator
            and "tba-concrete-capability" not in package.dependencies
            and ("tba-concrete-capability-default" not in package.dependencies)
        ):
            violations.append(
                Violation(
                    kind="missing-capability-implementation-dependency",
                    package=package.distribution,
                    package_layer=package.layer,
                    target="tba-concrete-capability",
                    target_layer="10-concrete",
                    path=manifest.relative_to(root).as_posix(),
                    line=None,
                    detail="layer-40 capabilities inherit layer-10.1 Capability or layer-10.2 DefaultCapability",
                )
            )
        for dependency in package.dependencies:
            target = by_distribution.get(dependency)
            if target is None or target.layer not in CAPABILITY_FORBIDDEN_LAYERS:
                continue
            violations.append(
                Violation(
                    kind="manifest-dependency",
                    package=package.distribution,
                    package_layer=package.layer,
                    target=target.distribution,
                    target_layer=target.layer,
                    path=manifest.relative_to(root).as_posix(),
                    line=None,
                    detail=(
                        "capabilities may use primitives, contracts, and layers 10, "
                        "20, 30, and 40; storage implementations and bases require "
                        "an implementation boundary"
                    ),
                )
            )

        for source in sorted((package.path / "src").rglob("*.py")):
            text = source.read_text(encoding="utf-8-sig")
            tree = ast.parse(text, filename=str(source))
            imports: dict[str, str] = {}
            source_imports: list[tuple[str, int]] = []

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        root_name = alias.name.split(".")[0]
                        imports[alias.asname or root_name] = root_name
                        source_imports.append((root_name, node.lineno))
                elif (
                    isinstance(node, ast.ImportFrom) and node.level == 0 and node.module
                ):
                    root_name = node.module.split(".")[0]
                    source_imports.append((root_name, node.lineno))
                    for alias in node.names:
                        imports[alias.asname or alias.name] = root_name

            for match in DYNAMIC_IMPORT_RE.finditer(text):
                source_imports.append(
                    (
                        match.group("module").split(".")[0],
                        text.count("\n", 0, match.start()) + 1,
                    )
                )

            relative_source = source.relative_to(root).as_posix()
            for import_root, line in sorted(set(source_imports)):
                target = by_import_root.get(import_root)
                if target is None or target.layer not in CAPABILITY_FORBIDDEN_LAYERS:
                    continue
                violations.append(
                    Violation(
                        kind="source-import",
                        package=package.distribution,
                        package_layer=package.layer,
                        target=target.distribution,
                        target_layer=target.layer,
                        path=relative_source,
                        line=line,
                        detail=f"imports first-party root {import_root!r}",
                    )
                )

            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                for base in node.bases:
                    import_root = _base_root(base, imports)
                    if import_root in CAPABILITY_IMPLEMENTATION_ROOTS:
                        has_capability_implementation = True
                        capability_implementation_count += 1
                    target = by_import_root.get(import_root or "")
                    if (
                        target is None
                        or target.layer not in CAPABILITY_FORBIDDEN_BASE_LAYERS
                    ):
                        continue
                    violations.append(
                        Violation(
                            kind="inheritance",
                            package=package.distribution,
                            package_layer=package.layer,
                            target=target.distribution,
                            target_layer=target.layer,
                            path=relative_source,
                            line=node.lineno,
                            detail=(
                                f"class {node.name!r} inherits from "
                                f"{ast.unparse(base)!r}"
                            ),
                        )
                    )

        if not is_compatibility_aggregator and not has_capability_implementation:
            violations.append(
                Violation(
                    kind="missing-capability-inheritance",
                    package=package.distribution,
                    package_layer=package.layer,
                    target="Capability",
                    target_layer="10-concrete",
                    path=package.path.relative_to(root).as_posix(),
                    line=None,
                    detail="no class inherits layer-10.1 Capability or layer-10.2 DefaultCapability",
                )
            )
        elif not is_compatibility_aggregator and capability_implementation_count != 1:
            violations.append(
                Violation(
                    kind="capability-owner-count",
                    package=package.distribution,
                    package_layer=package.layer,
                    target="one-primary-capability",
                    target_layer="architecture-policy",
                    path=package.path.relative_to(root).as_posix(),
                    line=None,
                    detail=(
                        "canonical layer-40 packages own exactly one direct "
                        f"Capability implementation; found {capability_implementation_count}"
                    ),
                )
            )

    return tuple(
        sorted(
            violations,
            key=lambda item: (
                item.package,
                item.kind,
                item.path,
                item.line or 0,
                item.target,
            ),
        )
    )


def report(violations: tuple[Violation, ...]) -> dict[str, object]:
    return {
        "layer_policy": {
            "layers": list(LAYER_POLICY.layer_ids),
            "dependency_rules": {
                rule.consumer_layer: sorted(rule.allowed_target_layers)
                for rule in LAYER_POLICY.dependency_rules
            },
            "dependency_exceptions": [
                {
                    "consumer": item.consumer,
                    "target": item.target,
                    "reason": item.reason,
                }
                for item in LAYER_POLICY.dependency_exceptions
            ],
        },
        "policy": {
            "consumer": "40-capabilities",
            "allowed_target_layers": sorted(CAPABILITY_ALLOWED_LAYERS),
            "forbidden_target_layers": sorted(CAPABILITY_FORBIDDEN_LAYERS),
            "forbidden_inheritance_layers": sorted(CAPABILITY_FORBIDDEN_BASE_LAYERS),
            "required_implementation_roots": sorted(CAPABILITY_IMPLEMENTATION_ROOTS),
            "compatibility_aggregators": sorted(CAPABILITY_COMPATIBILITY_AGGREGATORS),
        },
        "capability_purposes": dict(sorted(CAPABILITY_PURPOSES.items())),
        "violation_count": len(violations),
        "violations": [asdict(item) for item in violations],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args()
    violations = validate()
    if args.json:
        print(json.dumps(report(violations), indent=2))
    elif violations:
        for item in violations:
            location = f"{item.path}:{item.line}" if item.line else item.path
            print(
                f"{location}: {item.kind}: {item.package} ({item.package_layer}) "
                f"-> {item.target} ({item.target_layer}): {item.detail}"
            )
    else:
        print("layer boundary validation passed")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
