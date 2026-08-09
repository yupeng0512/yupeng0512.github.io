from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate-static-site.py"
SPEC = importlib.util.spec_from_file_location("validate_static_site", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class BuildProvenanceValidationTests(unittest.TestCase):
    def test_reviewed_mapping_set_is_fail_closed(self) -> None:
        contract_path = SCRIPT.parents[1] / "build-provenance.json"
        contract = json.loads(contract_path.read_text(encoding="utf-8"))

        with tempfile.TemporaryDirectory() as temporary_directory:
            original_root = MODULE.ROOT
            MODULE.ROOT = Path(temporary_directory)
            try:
                target = MODULE.ROOT / "build-provenance.json"
                target.write_text(json.dumps(contract), encoding="utf-8")
                failures: list[str] = []
                MODULE.validate_build_provenance({target.name}, failures)
                self.assertEqual(failures, [])

                contract["source_to_deployment_commits"][0]["deployment"] = "0" * 40
                target.write_text(json.dumps(contract), encoding="utf-8")
                failures = []
                MODULE.validate_build_provenance({target.name}, failures)
                self.assertEqual(
                    failures,
                    [
                        "source-to-deployment provenance must contain five reviewed mappings"
                    ],
                )
            finally:
                MODULE.ROOT = original_root


if __name__ == "__main__":
    unittest.main()
