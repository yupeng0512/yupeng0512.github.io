#!/usr/bin/env python3
"""Validate the recoverable contract of the deployed static site."""

from __future__ import annotations

import json
import posixpath
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_PORTFOLIO_SOURCE_COMMIT = "10c0ea912ec964cc50af26706571ed2ece88edd8"
EXPECTED_PROVENANCE_MAPPINGS = {
    (
        "b9d651c79c857a1d86ca2c107198d95745af0804",
        "4e15345abf7a95f1d2d6ee6c85d8987fdc35cd0c",
    ),
    (
        "21888fb78b0b7e5b040526fdf8e4710f1f31737e",
        "ee029f8853f7fda9b0a832cbead55d854180e459",
    ),
    (
        "57607d15c95ed78df839eed0cf757520f6e057be",
        "a317ead10f2dca33615a77dd6ca0705b4af0eb98",
    ),
    (
        "f11618126f1a9e70d6323ec8e0e94ade9bb8c55f",
        "c49be802c46851e91389011015cb0bb1dbda3389",
    ),
    (
        "10c0ea912ec964cc50af26706571ed2ece88edd8",
        "6b47dd27212f3346ea0a4ebc91ad7f429daf6a9d",
    ),
}


class ReferenceParser(HTMLParser):
    """Collect local-resource candidates from tolerant HTML parsing."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.references: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del tag
        values = dict(attrs)
        for key in ("href", "src", "poster"):
            value = values.get(key)
            if value:
                self.references.append(value)

        srcset = values.get("srcset")
        if srcset:
            self.references.extend(
                part.strip().split()[0] for part in srcset.split(",") if part.strip()
            )


def repository_files() -> set[str]:
    """Return tracked plus non-ignored untracked files for pre-commit checks."""

    output = subprocess.check_output(
        [
            "git",
            "-C",
            str(ROOT),
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
        ]
    )
    return {
        raw.decode("utf-8", "surrogateescape") for raw in output.split(b"\0") if raw
    }


def local_candidates(source: str, reference: str) -> set[str] | None:
    """Map a browser reference to the static files that could satisfy it."""

    if not reference or reference.startswith(
        ("#", "mailto:", "tel:", "javascript:", "data:", "//")
    ):
        return None

    parsed = urlsplit(reference)
    if parsed.scheme or parsed.netloc:
        return None

    raw_path = unquote(parsed.path)
    if not raw_path:
        return None

    if raw_path.startswith("/"):
        candidate = posixpath.normpath(raw_path.lstrip("/"))
    else:
        candidate = posixpath.normpath(
            posixpath.join(posixpath.dirname(source), raw_path)
        )

    if candidate.startswith("../"):
        return set()
    if candidate in ("", "."):
        candidate = "index.html"

    candidates = {candidate}
    if candidate.endswith("/"):
        candidates.add(candidate + "index.html")
    elif "." not in posixpath.basename(candidate):
        candidates.add(candidate + ".html")
        candidates.add(candidate + "/index.html")
    return candidates


def validate_json(paths: list[str], failures: list[str]) -> None:
    for path in paths:
        try:
            json.loads((ROOT / path).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            failures.append(f"invalid JSON: {path}: {type(error).__name__}")


def validate_build_provenance(files: set[str], failures: list[str]) -> None:
    path = "build-provenance.json"
    if path not in files:
        failures.append(f"missing build provenance: {path}")
        return

    try:
        contract = json.loads((ROOT / path).read_text(encoding="utf-8"))
        portfolio = contract["portfolio_source"]
        legacy = contract["legacy_hexo_archive"]
        mappings = contract["source_to_deployment_commits"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        failures.append(f"invalid build provenance contract: {type(error).__name__}")
        return

    if contract.get("schema_version") != 1:
        failures.append("build provenance schema_version must be 1")
    if portfolio.get("repository") != "https://github.com/yupeng0512/personal-card":
        failures.append("portfolio source repository is not the reviewed public source")
    if not COMMIT_SHA.fullmatch(str(portfolio.get("source_commit", ""))):
        failures.append("portfolio source_commit must be a full lowercase Git SHA")
    elif portfolio.get("source_commit") != EXPECTED_PORTFOLIO_SOURCE_COMMIT:
        failures.append(
            "portfolio source_commit must remain the rebuilt source snapshot"
        )
    if portfolio.get("verified_runtime") != {"node": "20.19.4", "npm": "10.8.2"}:
        failures.append("portfolio verified runtime must remain explicit")
    if portfolio.get("install_command") != "npm ci --no-audit --no-fund":
        failures.append("portfolio install must use the reviewed lockfile command")
    if portfolio.get("expected_output_files") != 124:
        failures.append("portfolio expected_output_files must remain the verified 124")
    if portfolio.get("build_command") != "./node_modules/.bin/astro build":
        failures.append(
            "portfolio cold build must not rescan the surrounding workspace"
        )
    if portfolio.get("frozen_input") != "src/data/workspace-data.json":
        failures.append("portfolio frozen input snapshot must remain explicit")
    if portfolio.get("comparison") != {
        "exact_bytes": "all non-HTML files",
        "html_normalization": "only the non-semantic astro-island uid attribute",
        "deployed_extra_files_allowed": True,
    }:
        failures.append("portfolio comparison boundary must remain fail closed")
    if legacy.get("source_status") != "not-located":
        failures.append(
            "legacy Hexo source must remain unresolved until independently proven"
        )
    if legacy.get("recovery_mode") != "deployment-artifacts-only":
        failures.append("legacy Hexo recovery must not claim an unproven source build")
    if not isinstance(mappings, list) or not all(
        isinstance(mapping, dict) for mapping in mappings
    ):
        failures.append("source-to-deployment provenance must be an object list")
    elif any(
        not COMMIT_SHA.fullmatch(str(mapping.get(field, "")))
        for mapping in mappings
        for field in ("source", "deployment")
    ):
        failures.append("source-to-deployment mappings require full lowercase Git SHAs")
    elif {
        (str(mapping["source"]), str(mapping["deployment"])) for mapping in mappings
    } != EXPECTED_PROVENANCE_MAPPINGS:
        failures.append(
            "source-to-deployment provenance must contain five reviewed mappings"
        )


def validate_gitalk(failures: list[str]) -> None:
    site_path = ROOT / "api/site.json"
    try:
        site = json.loads(site_path.read_text(encoding="utf-8"))
        gitalk = site["theme_config"]["gitalk"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        failures.append(f"cannot validate Gitalk configuration: {type(error).__name__}")
        return

    if gitalk.get("enable") is not False:
        failures.append("Gitalk must remain disabled in the public deployment")
    if gitalk.get("clientSecret"):
        failures.append("Gitalk clientSecret must be empty in the public deployment")


def validate_html(html_paths: list[str], files: set[str], failures: list[str]) -> int:
    reference_count = 0
    for path in html_paths:
        parser = ReferenceParser()
        try:
            parser.feed((ROOT / path).read_text(encoding="utf-8"))
        except (OSError, UnicodeError) as error:
            failures.append(f"invalid HTML input: {path}: {type(error).__name__}")
            continue

        for reference in parser.references:
            reference_count += 1
            candidates = local_candidates(path, reference)
            if candidates is not None and not candidates.intersection(files):
                failures.append(f"broken local reference: {path}: {reference}")
    return reference_count


def main() -> int:
    files = repository_files()
    failures: list[str] = []

    tracked_macos_metadata = sorted(
        path for path in files if posixpath.basename(path) == ".DS_Store"
    )
    failures.extend(
        f"tracked macOS metadata: {path}" for path in tracked_macos_metadata
    )

    json_paths = sorted(path for path in files if path.endswith(".json"))
    html_paths = sorted(path for path in files if path.endswith(".html"))
    validate_json(json_paths, failures)
    validate_build_provenance(files, failures)
    validate_gitalk(failures)
    reference_count = validate_html(html_paths, files, failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        print(f"validation failed with {len(failures)} issue(s)", file=sys.stderr)
        return 1

    print(
        "validation passed: "
        f"files={len(files)} html={len(html_paths)} json={len(json_paths)} "
        f"references={reference_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
