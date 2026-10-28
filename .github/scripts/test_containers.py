#!/usr/bin/env python3
"""Regression checks for the required CI gate's affected-container selection."""

import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('containers', Path(__file__).with_name('containers.py'))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SelectionTests(unittest.TestCase):
    containers = {'aria2': {}, 'other-app': {}}

    def test_only_changed_container_is_selected(self):
        self.assertEqual(MODULE.select(self.containers, ['aria2/Containerfile']), ['aria2'])

    def test_shared_workflow_changes_test_every_container(self):
        self.assertEqual(MODULE.select(self.containers, ['.github/workflows/build-container.yml']),
                         ['aria2', 'other-app'])

    def test_docs_only_has_no_native_builds(self):
        self.assertEqual(MODULE.select(self.containers, ['README.md']), [])

    def test_similar_prefix_is_not_a_container_change(self):
        self.assertEqual(MODULE.select(self.containers, ['aria2-other/Containerfile']), [])


if __name__ == '__main__':
    unittest.main()
