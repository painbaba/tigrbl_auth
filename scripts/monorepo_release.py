from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised by Python 3.10 CI
    import tomli as tomllib  # type: ignore[no-redef]

ROOT = Path(__file__).resolve().parents[1]
TAG_RE = re.compile(r"^(?P<name>[A-Za-z0-9_.-]+)==(?P<version>\d+\.\d+\.\d+(?:\.dev\d+)?(?:[-+][A-Za-z0-9_.-]+)?)$")
REQ_NAME_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)")
SUPPORTED_PYTHON_VERSIONS = ("3.10", "3.11", "3.12", "3.13", "3.14")
TESTKIT_PACKAGE_NAME = "tba-testkit-identity"
SWARMAURI_PYTHON_CEILING = (3, 13)
TIGRBL_PYTHON_CEILING = (3, 14)


@dataclass(frozen=True)
class Package:
    name: str
    version: str
    path: Path
    import_root: str

    def as_cell(self) -> dict[str, str]:
        return {
            "name": self.name,
            "version": self.version,
            "path": self.path.as_posix(),
            "import_root": self.import_root,
            "tag": f"{self.name}=={self.version}",
        }


def _python_tag(version: str) -> str:
    return f"py{version.replace('.', '')}"


def _load_pyproject(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _package_import_root(package_path: Path, name: str) -> str:
    src = package_path / "src"
    if src.exists():
        roots = sorted(item.name for item in src.iterdir() if item.is_dir())
        if roots:
            return roots[0]
    return name.replace("-", "_")


def discover_packages() -> list[Package]:
    packages: list[Package] = []
    for pyproject in sorted((ROOT / "pkgs").rglob("pyproject.toml")):
        if pyproject.relative_to(ROOT / "pkgs").parts[0] == "deprecated":
            continue
        data = _load_pyproject(pyproject)
        project = data.get("project", {})
        name = str(project.get("name") or "").strip()
        version = str(project.get("version") or "").strip()
        if not name or not version:
            raise SystemExit(f"missing project.name or project.version in {pyproject.relative_to(ROOT)}")
        package_path = pyproject.parent.relative_to(ROOT)
        packages.append(
            Package(
                name=name,
                version=version,
                path=package_path,
                import_root=_package_import_root(pyproject.parent, name),
            )
        )
    return packages


def _find_package(name: str) -> Package:
    matches = [item for item in discover_packages() if item.name == name]
    if not matches:
        known = ", ".join(item.name for item in discover_packages())
        raise SystemExit(f"unknown package {name!r}; known packages: {known}")
    return matches[0]


def _write_github_output(values: dict[str, str]) -> None:
    output_name = os.environ.get("GITHUB_OUTPUT", "")
    if not output_name:
        print(json.dumps(values, indent=2))
        return
    output = Path(output_name)
    with output.open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def cmd_matrix(args: argparse.Namespace) -> int:
    cells = [item.as_cell() for item in discover_packages()]
    payload = json.dumps(cells, separators=(",", ":"))
    _write_github_output({"matrix": payload, "count": str(len(cells))})
    if args.print:
        print(json.dumps(cells, indent=2))
    return 0


def cmd_release_matrix(args: argparse.Namespace) -> int:
    packages = discover_packages()
    if args.package != "all" and not any(p.name == args.package for p in packages):
        raise SystemExit(f"unknown package {args.package!r}")
    # Cross-job outputs must not contain public metadata that can match a
    # repository secret. Resolve these indices at the same immutable revision.
    cells = [
        {"index": index}
        for index, package in enumerate(packages)
        if (args.package == "all" or package.name == args.package)
        and _supported_package_python_versions(package, ["3.12"])
    ]
    _write_github_output({"matrix": json.dumps(cells, separators=(",", ":")), "count": str(len(cells))})
    return 0


def cmd_resolve_release_index(args: argparse.Namespace) -> int:
    packages = discover_packages()
    if not 0 <= args.index < len(packages):
        raise SystemExit(f"invalid release package index {args.index}")
    package = packages[args.index]
    if args.package != "all" and package.name != args.package:
        raise SystemExit("release package index does not match selected package")
    _write_github_output(package.as_cell())
    return 0


def cmd_resolve_tag(args: argparse.Namespace) -> int:
    match = TAG_RE.match(args.tag)
    if match is None:
        raise SystemExit(f"tag must match <package>==<version>; got {args.tag!r}")
    package = _find_package(match.group("name"))
    version = match.group("version")
    if package.version != version:
        raise SystemExit(
            f"tag version {version!r} does not match {package.name} pyproject version {package.version!r}"
        )
    cell = package.as_cell()
    _write_github_output(
        {
            "package_name": package.name,
            "package_version": package.version,
            "package_path": package.path.as_posix(),
            "import_root": package.import_root,
            "tag": cell["tag"],
            "matrix": json.dumps([cell], separators=(",", ":")),
        }
    )
    print(json.dumps(cell, indent=2))
    return 0


def _run(args: list[str]) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def _run_capture(args: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(args, cwd=cwd or ROOT, check=True, text=True, stdout=subprocess.PIPE)
    return result.stdout.strip()


def _normalize_dist_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _dependency_name(requirement: str) -> str | None:
    match = REQ_NAME_RE.match(requirement)
    if match is None:
        return None
    return _normalize_dist_name(match.group(1))


def _project_dependencies(package: Package) -> list[str]:
    data = _load_pyproject(ROOT / package.path / "pyproject.toml")
    dependencies = data.get("project", {}).get("dependencies", [])
    return [str(item) for item in dependencies]


def _local_dependency_closure(package: Package) -> list[Package]:
    packages = discover_packages()
    by_name = {_normalize_dist_name(item.name): item for item in packages}
    root_name = _normalize_dist_name(package.name)
    pending = [package]
    seen: set[str] = set()
    closure: list[Package] = []

    while pending:
        current = pending.pop()
        for requirement in _project_dependencies(current):
            dep_name = _dependency_name(requirement)
            if dep_name is None or dep_name == root_name or dep_name in seen:
                continue
            dependency = by_name.get(dep_name)
            if dependency is None:
                continue
            seen.add(dep_name)
            closure.append(dependency)
            pending.append(dependency)
    return closure


def _python_minor(version: str) -> tuple[int, int]:
    major, minor = version.split(".", 1)
    return int(major), int(minor)


def _declared_dependency_requirements(package: Package) -> list[str]:
    requirements = list(_project_dependencies(package))
    for dependency in _local_dependency_closure(package):
        requirements.extend(_project_dependencies(dependency))
    return requirements


def _supported_package_python_versions(package: Package, versions: list[str]) -> list[str]:
    requirements = _declared_dependency_requirements(package)
    compatible: list[str] = []
    for version in versions:
        python_minor = _python_minor(version)
        if package.name == TESTKIT_PACKAGE_NAME and python_minor >= SWARMAURI_PYTHON_CEILING:
            continue
        blocked = False
        for requirement in requirements:
            dep_name = _dependency_name(requirement)
            if dep_name is None:
                continue
            if dep_name.startswith("swarmauri-") and python_minor >= SWARMAURI_PYTHON_CEILING:
                blocked = True
                break
            if dep_name == "tigrbl" and python_minor >= TIGRBL_PYTHON_CEILING:
                blocked = True
                break
        if not blocked:
            compatible.append(version)
    return compatible


def cmd_create_tags(args: argparse.Namespace) -> int:
    packages = discover_packages() if args.package == "all" else [_find_package(args.package)]
    created: list[str] = []
    for package in packages:
        version = args.version or package.version
        if version != package.version:
            raise SystemExit(
                f"requested version {version!r} does not match {package.name} pyproject version {package.version!r}"
            )
        tag = f"{package.name}=={version}"
        exists = subprocess.run(
            ["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}"],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode == 0
        if exists and not args.force:
            print(f"tag exists, skipping: {tag}")
            continue
        if exists:
            _run(["git", "tag", "-d", tag])
            _run(["git", "push", "--delete", "origin", tag])
        _run(["git", "tag", "-a", tag, "-m", f"Release {tag}"])
        _run(["git", "push", "origin", tag])
        created.append(tag)
    print(json.dumps({"created": created}, indent=2))
    return 0


def cmd_test_matrix(args: argparse.Namespace) -> int:
    packages = discover_packages() if args.package == "all" else [_find_package(args.package)]
    versions = args.python_version or list(SUPPORTED_PYTHON_VERSIONS)
    unknown = sorted(set(versions) - set(SUPPORTED_PYTHON_VERSIONS))
    if unknown:
        raise SystemExit(f"unsupported Python versions requested: {', '.join(unknown)}")

    cells = []
    for package in packages:
        for version in _supported_package_python_versions(package, versions):
            package_test_paths = [
                f"tests/packages/{package.name}",
                f"tests/packages/{package.import_root}",
            ]
            pre_test_command = ""
            pytest_args = ""
            cross_cutting = package.name == TESTKIT_PACKAGE_NAME
            if cross_cutting:
                package_test_paths.append("tests/interop")
                pre_test_command = '$VENV_PYTHON -m pip install -e ".[test,sqlite,postgres,servers]"'
                pytest_args = "--certification-lane\nall"
            cell = package.as_cell()
            cell.update(
                {
                    "python_version": version,
                    "python_tag": _python_tag(version),
                    "cell_id": f"{package.name}-{_python_tag(version)}",
                    "workspace_source_globs": "pkgs/*/*/src\npkgs/deprecated/*/src",
                    "package_test_paths": "\n".join(package_test_paths),
                    "pre_test_command": pre_test_command,
                    "pytest_args": pytest_args,
                    "cross_cutting": str(cross_cutting).lower(),
                }
            )
            cells.append(cell)
    payload = json.dumps(cells, separators=(",", ":"))
    _write_github_output({"matrix": payload, "count": str(len(cells))})
    if args.print:
        print(json.dumps(cells, indent=2))
    return 0


def _venv_python(venv: Path) -> Path:
    if sys.platform == "win32":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def _find_built_wheel(package: Package, dist_dir: Path) -> Path:
    wheels = sorted(dist_dir.glob("*.whl"))
    if not wheels:
        raise SystemExit(f"no wheel found for {package.name} in {dist_dir}")
    normalized = package.name.replace("-", "_")
    matching = [wheel for wheel in wheels if wheel.name.startswith(f"{normalized}-{package.version}-")]
    if matching:
        return matching[0]
    return wheels[0]


def _venv_site_packages(python: Path) -> Path:
    output = _run_capture(
        [
            str(python),
            "-c",
            "import site; print(site.getsitepackages()[0])",
        ]
    )
    return Path(output)


def _built_local_wheel_path(package: Package, wheelhouse: Path) -> Path:
    wheel_prefix = _normalize_dist_name(package.name).replace("-", "_")
    candidates = sorted(wheelhouse.glob(f"{wheel_prefix}-{package.version}-*.whl"))
    if not candidates:
        raise SystemExit(
            f"built wheel for {package.name}=={package.version} not found in {wheelhouse}"
        )
    return candidates[-1]


def _build_local_dependency_wheels(package: Package, wheelhouse: Path) -> list[Path]:
    dependencies = _local_dependency_closure(package)
    wheelhouse.mkdir(parents=True, exist_ok=True)
    wheels: list[Path] = []
    for dependency in dependencies:
        _run(
            [
                "uv",
                "build",
                "--project",
                str(ROOT / dependency.path),
                "--out-dir",
                str(wheelhouse),
            ]
        )
        wheels.append(_built_local_wheel_path(dependency, wheelhouse))
    return wheels


def _root_project_package() -> Package:
    project = _load_pyproject(ROOT / "pyproject.toml").get("project", {})
    name = str(project.get("name") or "tba-auth")
    version = str(project.get("version") or "0.0.0")
    return Package(name=name, version=version, path=Path("."), import_root="tba_auth")


def _build_testkit_root_dependency_wheels(wheelhouse: Path) -> list[Path]:
    return _build_local_dependency_wheels(_root_project_package(), wheelhouse)


def _materialize_testkit_interop_artifacts(python: Path) -> None:
    code = """
from scripts.materialize_tier4_peer_evidence import (
    load_counterparts,
    load_peer_profiles,
    materialize_external_handoff_templates,
)

materialize_external_handoff_templates(load_peer_profiles(), load_counterparts())
"""
    subprocess.run([str(python), "-c", code], cwd=ROOT, check=True)


def _package_test_paths(package: Package) -> list[Path]:
    candidates = [
        ROOT / "tests" / "packages" / package.name,
        ROOT / "tests" / "packages" / package.import_root,
    ]
    if package.name == TESTKIT_PACKAGE_NAME:
        candidates.append(ROOT / "tests" / "interop")
    return [path for path in candidates if path.exists()]


def _install_package_test_harness(python: Path) -> None:
    subprocess.run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "-e",
            ".[test]",
        ],
        cwd=ROOT,
        check=True,
    )


def cmd_isolated_test(args: argparse.Namespace) -> int:
    package = _find_package(args.package)
    expected_minor = tuple(int(part) for part in args.python_version.split("."))
    actual_minor = sys.version_info[:2]
    if actual_minor != expected_minor:
        raise SystemExit(
            f"expected Python {args.python_version}, running {actual_minor[0]}.{actual_minor[1]}"
        )

    dist_dir = (ROOT / args.dist_dir).resolve()
    wheel = _find_built_wheel(package, dist_dir)
    work_dir = (ROOT / args.work_dir / package.name / _python_tag(args.python_version)).resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    venv = work_dir / ".venv"
    if venv.exists():
        shutil.rmtree(venv)
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    python = _venv_python(venv)

    wheelhouse = work_dir / "local-wheelhouse"
    if wheelhouse.exists():
        shutil.rmtree(wheelhouse)
    local_dependency_wheels = _build_local_dependency_wheels(package, wheelhouse)
    install_command = [
        str(python),
        "-m",
        "pip",
        "install",
        *[str(path) for path in local_dependency_wheels],
        str(wheel),
    ]
    subprocess.run(install_command, check=True)
    subprocess.run([str(python), "-m", "pip", "check"], check=True)

    check_code = """
import importlib
import importlib.metadata
import json
import sys

dist_name = sys.argv[1]
import_root = sys.argv[2]
expected_version = sys.argv[3]

module = importlib.import_module(import_root)
version = importlib.metadata.version(dist_name)
assert module.__name__ == import_root, module.__name__
assert version == expected_version, version
print(json.dumps({"package": dist_name, "import_root": import_root, "version": version}))
"""
    output = _run_capture(
        [str(python), "-c", check_code, package.name, package.import_root, package.version],
        cwd=work_dir,
    )
    print(output)

    package_test_paths = _package_test_paths(package)
    if package_test_paths:
        if package.name == TESTKIT_PACKAGE_NAME:
            root_dependency_wheels = _build_testkit_root_dependency_wheels(wheelhouse)
            for path in root_dependency_wheels:
                if path not in local_dependency_wheels:
                    local_dependency_wheels.append(path)
            subprocess.run(
                [
                    str(python),
                    "-m",
                    "pip",
                    "install",
                    *[str(path) for path in root_dependency_wheels],
                ],
                check=True,
            )
            subprocess.run(
                [
                    str(python),
                    "-m",
                    "pip",
                    "install",
                    "--find-links",
                    str(wheelhouse),
                    "-e",
                    ".[test,sqlite,postgres,servers]",
                ],
                cwd=ROOT,
                check=True,
            )
            _materialize_testkit_interop_artifacts(python)
        _install_package_test_harness(python)
        env = os.environ.copy()
        env.update(
            {
                "PACKAGE_UNDER_TEST": package.name,
                "IMPORT_ROOT_UNDER_TEST": package.import_root,
                "PACKAGE_VERSION_UNDER_TEST": package.version,
                "TBA_AUTH_PACKAGE_UNDER_TEST": package.name,
                "TBA_AUTH_IMPORT_ROOT_UNDER_TEST": package.import_root,
                "TBA_AUTH_PACKAGE_VERSION_UNDER_TEST": package.version,
                "VENV_PYTHON": str(python),
                "VENV_BIN": str(python.parent),
            }
        )
        pytest_args = []
        if package.name == TESTKIT_PACKAGE_NAME:
            pytest_args.extend(["--certification-lane", "all"])
        subprocess.run(
            [
                str(python),
                "-m",
                "pytest",
                *pytest_args,
                *[str(path) for path in package_test_paths],
            ],
            cwd=ROOT,
            env=env,
            check=True,
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Monorepo package release helpers.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    matrix = subparsers.add_parser("matrix")
    matrix.add_argument("--print", action="store_true")
    matrix.set_defaults(func=cmd_matrix)

    release_matrix = subparsers.add_parser("release-matrix")
    release_matrix.add_argument("--package", default="all")
    release_matrix.set_defaults(func=cmd_release_matrix)

    release_index = subparsers.add_parser("resolve-release-index")
    release_index.add_argument("--index", required=True, type=int)
    release_index.add_argument("--package", default="all")
    release_index.set_defaults(func=cmd_resolve_release_index)

    resolve = subparsers.add_parser("resolve-tag")
    resolve.add_argument("tag")
    resolve.set_defaults(func=cmd_resolve_tag)

    tags = subparsers.add_parser("create-tags")
    tags.add_argument("--package", default="all", help="Package name or 'all'.")
    tags.add_argument("--version", default="", help="Optional explicit version; must match pyproject.")
    tags.add_argument("--force", action="store_true", help="Replace existing tags.")
    tags.set_defaults(func=cmd_create_tags)

    test_matrix = subparsers.add_parser("test-matrix")
    test_matrix.add_argument("--package", default="all", help="Package name or 'all'.")
    test_matrix.add_argument("--python-version", action="append", choices=SUPPORTED_PYTHON_VERSIONS)
    test_matrix.add_argument("--print", action="store_true")
    test_matrix.set_defaults(func=cmd_test_matrix)

    isolated = subparsers.add_parser("isolated-test")
    isolated.add_argument("--package", required=True)
    isolated.add_argument("--python-version", required=True, choices=SUPPORTED_PYTHON_VERSIONS)
    isolated.add_argument("--dist-dir", required=True)
    isolated.add_argument("--work-dir", default=".tmp/package-isolation")
    isolated.set_defaults(func=cmd_isolated_test)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
