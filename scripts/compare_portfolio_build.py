#!/usr/bin/env python3
"""Compare a pinned personal-card build with the deployed Pages tree."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASTRO_ISLAND_UID = re.compile(rb'(<astro-island\b[^>]*?\s)uid="[^"]+"')


def normalize_for_comparison(path: Path, content: bytes) -> bytes:
    """Remove only Astro's non-semantic, per-build island UID from HTML."""

    if path.suffix.lower() != ".html":
        return content
    return ASTRO_ISLAND_UID.sub(rb'\1uid="NORMALIZED"', content)


def compare_build(source_dist: Path, deployed_root: Path) -> list[str]:
    """Return stable, path-only mismatches for the source build subset."""

    failures: list[str] = []
    source_paths = sorted(path for path in source_dist.rglob("*") if path.is_file())
    for source_path in source_paths:
        relative_path = source_path.relative_to(source_dist)
        deployed_path = deployed_root / relative_path
        if not deployed_path.is_file():
            failures.append(f"missing: {relative_path.as_posix()}")
            continue
        source_content = normalize_for_comparison(
            relative_path, source_path.read_bytes()
        )
        deployed_content = normalize_for_comparison(
            relative_path, deployed_path.read_bytes()
        )
        if source_content != deployed_content:
            failures.append(f"different: {relative_path.as_posix()}")
    return failures


def git_head(repository: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repository), "rev-parse", "HEAD"], text=True
    ).strip()


def load_contract(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify the pinned personal-card output inside this Pages tree."
    )
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="personal-card checkout at the pinned source commit, with dist already built",
    )
    parser.add_argument("--deployed", type=Path, default=ROOT)
    parser.add_argument("--contract", type=Path, default=ROOT / "build-provenance.json")
    args = parser.parse_args()

    try:
        contract = load_contract(args.contract)
        portfolio = contract["portfolio_source"]
        expected_commit = str(portfolio["source_commit"])
        expected_files = int(portfolio["expected_output_files"])
        actual_commit = git_head(args.source)
        source_dist = args.source / "dist"
        source_files = sum(1 for path in source_dist.rglob("*") if path.is_file())
    except (
        OSError,
        KeyError,
        TypeError,
        ValueError,
        subprocess.CalledProcessError,
    ) as error:
        print(
            f"FAIL: invalid provenance input: {type(error).__name__}", file=sys.stderr
        )
        return 1

    failures: list[str] = []
    if actual_commit != expected_commit:
        failures.append(
            f"source commit mismatch: expected {expected_commit}, got {actual_commit}"
        )
    if source_files != expected_files:
        failures.append(
            f"source file count mismatch: expected {expected_files}, got {source_files}"
        )
    failures.extend(compare_build(source_dist, args.deployed))

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        print(
            f"provenance comparison failed with {len(failures)} issue(s)",
            file=sys.stderr,
        )
        return 1

    html_files = sum(1 for path in source_dist.rglob("*.html") if path.is_file())
    print(
        "provenance comparison passed: "
        f"source_commit={actual_commit} files={source_files} html={html_files}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
