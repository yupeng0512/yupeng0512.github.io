from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "compare_portfolio_build.py"
SPEC = importlib.util.spec_from_file_location("compare_portfolio_build", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ComparePortfolioBuildTests(unittest.TestCase):
    def test_astro_island_uid_is_the_only_normalized_html_field(self) -> None:
        rebuilt = b'<astro-island uid="fresh" props="same"></astro-island>'
        deployed = b'<astro-island uid="old" props="same"></astro-island>'

        self.assertEqual(
            MODULE.normalize_for_comparison(Path("index.html"), rebuilt),
            MODULE.normalize_for_comparison(Path("index.html"), deployed),
        )
        self.assertNotEqual(
            MODULE.normalize_for_comparison(
                Path("index.html"), rebuilt.replace(b'props="same"', b'props="changed"')
            ),
            MODULE.normalize_for_comparison(Path("index.html"), deployed),
        )

    def test_compare_build_requires_source_files_and_exact_non_html_bytes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source-dist"
            deployed = root / "deployed"
            source.mkdir()
            deployed.mkdir()
            (source / "index.html").write_text(
                '<astro-island uid="fresh"></astro-island>', encoding="utf-8"
            )
            (deployed / "index.html").write_text(
                '<astro-island uid="old"></astro-island>', encoding="utf-8"
            )
            (source / "asset.js").write_bytes(b"same")
            (deployed / "asset.js").write_bytes(b"same")
            (deployed / "legacy-only.html").write_text("kept", encoding="utf-8")

            self.assertEqual(MODULE.compare_build(source, deployed), [])

            (deployed / "asset.js").write_bytes(b"different")
            self.assertEqual(
                MODULE.compare_build(source, deployed), ["different: asset.js"]
            )
            (deployed / "asset.js").unlink()
            self.assertEqual(
                MODULE.compare_build(source, deployed), ["missing: asset.js"]
            )


if __name__ == "__main__":
    unittest.main()
