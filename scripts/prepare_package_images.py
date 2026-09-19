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
    _, build_type, target = parts
    release_types = ("MinSizeRel", "Release", "RelWithDebInfo")
    if build_type not in release_types or not target or target.endswith("-dbg"):
        return []
    # Exact names: never substitute another version, a Debug build, or a
    # similarly suffixed target (for example custom-14.2.0 for 14.2.0).
    return [
        path
        for candidate_type in release_types
        if candidate_type != build_type
        for path in [build_root / f"image-{candidate_type}-{target}"]
        if path.is_dir()
    ]


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

    repairs = []
    missing = []
    for dependency in dependencies:
        instance = dependency.instance
        if isinstance(instance, SourceOnlyPackageBase):
            continue

        desired = Path(instance.imageDir())
        if desired.is_dir():
            continue

        # Build #51 installed these unchanged MinGW runtime DLLs during
        # bootstrap as MinSizeRel. Do not generalize this exception to Qt,
        # other dependencies, or the application we must actually compile.
        candidates = (
            compatible_image_candidates(desired.parent, desired.name)
            if dependency.path == "libs/runtime"
            else []
        )
        if not candidates:
            missing.append((str(dependency), str(desired)))
            continue

        source = candidates[0]
        repairs.append((dependency, source, desired))

    if missing:
        details = "\n".join(f"- {name}: {path}" for name, path in missing)
        raise RuntimeError(
            "Packaging dependencies are missing Craft image directories and no compatible "
            f"image exists:\n{details}"
        )

    # Validate the complete package before creating any junctions.
    for dependency, source, desired in repairs:
        print(f"Packaging image compatibility: {dependency}: {desired.name} -> {source.name}")
        create_windows_junction(source, desired)

    print(f"Packaging image preparation complete; repaired {len(repairs)} image path(s).")
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
