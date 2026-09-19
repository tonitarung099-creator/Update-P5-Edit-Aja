#!/usr/bin/env python3
"""Prepare Craft dependency image directories required by Windows packaging."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def compatible_image_candidates(build_root: Path, desired_name: str) -> list[Path]:
    """Return compatible sibling image directories for a missing Craft image."""
    if not desired_name.startswith("image-"):
        return []
    parts = desired_name.split("-", 2)
    if len(parts) != 3:
        return []
    _, _build_type, target = parts
    candidates = []
    for path in build_root.glob(f"image-*-{target}"):
        if path.name == desired_name or path.name.endswith("-dbg") or not path.is_dir():
            continue
        candidates.append(path)
    preference = {"MinSizeRel": 0, "Release": 1, "RelWithDebInfo": 2, "Debug": 3}
    return sorted(
        candidates,
        key=lambda p: (preference.get(p.name.split("-", 2)[1], 99), p.name),
    )


def create_windows_junction(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(destination), str(source)],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Could not create packaging image junction {destination} -> {source}: "
            f"{result.stdout}{result.stderr}"
        )


def prepare(craft_root: Path, package_name: str) -> int:
    craft_bin = craft_root / "craft" / "bin"
    if not craft_bin.is_dir():
        raise RuntimeError(f"Craft bin directory not found: {craft_bin}")
    sys.path.insert(0, str(craft_bin))

    from Blueprints.CraftDependencyPackage import CraftDependencyPackage, DependencyType
    from Blueprints.CraftPackageObject import CraftPackageObject
    from Package.SourceOnlyPackageBase import SourceOnlyPackageBase

    package = CraftPackageObject.get(package_name)
    if package is None:
        raise RuntimeError(f"Craft package not found: {package_name}")

    owner = package.instance
    dependencies = CraftDependencyPackage(package).getDependencies(
        depType=DependencyType.Runtime | DependencyType.Packaging,
        ignoredPackages=owner.ignoredPackages,
    )

    repaired = 0
    missing = []
    for dependency in dependencies:
        instance = dependency.instance
        if isinstance(instance, SourceOnlyPackageBase):
            continue

        desired = Path(instance.imageDir())
        if desired.is_dir():
            continue

        candidates = compatible_image_candidates(Path(instance.buildRoot()), desired.name)
        if not candidates:
            missing.append((str(dependency), str(desired)))
            continue

        source = candidates[0]
        print(f"Packaging image compatibility: {dependency}: {desired.name} -> {source.name}")
        create_windows_junction(source, desired)
        repaired += 1

    if missing:
        details = "\n".join(f"- {name}: {path}" for name, path in missing)
        raise RuntimeError(
            "Packaging dependencies are missing Craft image directories and no compatible "
            f"image exists:\n{details}"
        )

    print(f"Packaging image preparation complete; repaired {repaired} image path(s).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--craft-root",
        type=Path,
        default=Path(os.environ.get("CRAFT_ROOT", r"C:\CraftRoot")),
    )
    parser.add_argument("--package", default="kde/kdemultimedia/editaja")
    args = parser.parse_args()
    return prepare(args.craft_root.resolve(), args.package)


if __name__ == "__main__":
    raise SystemExit(main())
