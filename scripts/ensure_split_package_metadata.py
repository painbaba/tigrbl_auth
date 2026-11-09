"""Ensure every active split package has ownership docs and a typing marker."""

from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[1]
LAYER_OWNERSHIP = {
    "00-primitives": "dependency-light primitive vocabulary",
    "01-storage": "durable table and migration truth",
    "02-contracts": "protocol-neutral contracts and ports",
    "03-codecs": "reusable wire encoding and decoding",
    "05-bases": "reusable implementation bases",
    "10-concrete": "deterministic concrete value semantics",
    "20-providers": "environment-backed provider integration",
    "30-storage-runtime": "repository and storage-runtime composition",
    "40-capabilities": "cross-provider capability orchestration",
    "50-protocols": "versioned protocol composition and compatibility",
    "55-profiles": "profile selection and protocol constraints",
    "60-runtime": "runtime assembly and operator tooling",
    "70-facade": "stable compatibility facade exports",
    "80-routers": "reusable Tigrbl router composition",
    "85-middleware": "ASGI application middleware adapters",
    "90-backend-apps": "deployable backend application composition",
    "100-uix-core": "browser-safe reusable UIX components and clients",
    "105-ui": "product-specific browser applications",
    "110-examples": "runnable public-surface examples",
    "120-tests": "reusable test fixtures, vectors, and harnesses",
}


def main() -> None:
    for layer, ownership in LAYER_OWNERSHIP.items():
        for package in sorted((ROOT / "pkgs" / layer).glob("*/pyproject.toml")):
            package_root = package.parent
            metadata = tomllib.loads(package.read_text(encoding="utf-8"))
            distribution = str(metadata["project"]["name"])
            readme = package_root / "README.md"
            if not readme.exists():
                readme.write_text(
                    f"# {distribution}\n\nOwns {ownership}.\n\n"
                    "## Non-goals\n\nHigher-layer orchestration, lower-layer persistence, and protocol behavior outside this package's declared layer are not owned here.\n",
                    encoding="utf-8",
                )
            source = package_root / "src"
            if not source.is_dir():
                continue
            roots = [item for item in source.iterdir() if item.is_dir()]
            if len(roots) == 1:
                (roots[0] / "py.typed").touch()


if __name__ == "__main__":
    main()
