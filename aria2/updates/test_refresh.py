#!/usr/bin/env python3
"""Offline regression tests for coupled release-version/checksum updates."""

import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location("refresh", Path(__file__).with_name("refresh.py"))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RefreshTests(unittest.TestCase):
    manifest = {"dependencies": [{"arg": "VERSION", "assets": [
        {"arg": "AMD64_SHA256"}, {"arg": "ARM64_SHA256"}]}]}
    old = "ARG VERSION=1.0.0\nARG AMD64_SHA256=old64\nARG ARM64_SHA256=oldarm\n"

    @staticmethod
    def fetch(_dependency, _version):
        return {"AMD64_SHA256": "new64", "ARM64_SHA256": "newarm"}

    def test_bump_refreshes_both_architectures(self):
        candidate = self.old.replace("VERSION=1.0.0", "VERSION=1.1.0")
        result = MODULE.refresh(candidate, self.old, self.manifest, self.fetch)
        self.assertIn("ARG VERSION=1.1.0", result)
        self.assertIn("ARG AMD64_SHA256=new64", result)
        self.assertIn("ARG ARM64_SHA256=newarm", result)

    def test_same_version_replaced_asset_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "without a version change"):
            MODULE.refresh(self.old, self.old, self.manifest, self.fetch)

    def test_check_mode_refuses_stale_hashes(self):
        candidate = self.old.replace("VERSION=1.0.0", "VERSION=1.1.0")
        with self.assertRaisesRegex(ValueError, "Checksum mismatch"):
            MODULE.refresh(candidate, self.old, self.manifest, self.fetch, check=True)

    def test_current_hashes_are_left_unchanged(self):
        current = self.old.replace("old64", "new64").replace("oldarm", "newarm")
        self.assertEqual(MODULE.refresh(current, current, self.manifest, self.fetch, check=True), current)

    def test_ambiguous_argument_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "exactly one"):
            MODULE.argument(self.old + "ARG VERSION=2.0.0\n", "VERSION")

    def test_failed_asset_lookup_leaves_input_untouched(self):
        def missing(_dependency, _version):
            raise ValueError("Missing release asset")
        with self.assertRaisesRegex(ValueError, "Missing release asset"):
            MODULE.refresh(self.old.replace("1.0.0", "1.1.0"), self.old, self.manifest, missing)
        self.assertIn("old64", self.old)


if __name__ == "__main__":
    unittest.main()
