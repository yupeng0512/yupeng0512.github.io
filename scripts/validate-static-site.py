#!/usr/bin/env python3
"""Validate the recoverable contract of the deployed static site."""

from __future__ import annotations

import json
import posixpath
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]


class ReferenceParser(HTMLParser):
    """Collect local-resource candidates from tolerant HTML parsing."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.references: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        del tag
        values = dict(attrs)
        for key in ("href", "src", "poster"):
            value = values.get(key)
            if value:
                self.references.append(value)

        srcset = values.get("srcset")
        if srcset:
            self.references.extend(
                part.strip().split()[0]
                for part in srcset.split(",")
                if part.strip()
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
        raw.decode("utf-8", "surrogateescape")
        for raw in output.split(b"\0")
        if raw
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


def validate_html(
    html_paths: list[str], files: set[str], failures: list[str]
) -> int:
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
    failures.extend(f"tracked macOS metadata: {path}" for path in tracked_macos_metadata)

    json_paths = sorted(path for path in files if path.endswith(".json"))
    html_paths = sorted(path for path in files if path.endswith(".html"))
    validate_json(json_paths, failures)
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
