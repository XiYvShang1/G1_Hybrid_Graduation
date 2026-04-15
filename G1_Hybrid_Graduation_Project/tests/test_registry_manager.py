"""Regression tests for registry reset and upsert semantics."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from G1_Hybrid_Graduation_Project.registry_manager import (
    load_registry_bundle,
    load_yaml_config,
    reset_registry_to_examples,
    upsert_registry_item,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RegistryManagerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="g1_hybrid_registry_test_"))
        shutil.copytree(PROJECT_ROOT / "configs", self.temp_dir / "configs")
        shutil.copytree(PROJECT_ROOT / "registry", self.temp_dir / "registry")

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def test_reset_registry_restores_expected_example_counts(self) -> None:
        reset_registry_to_examples(self.temp_dir)

        bundle = load_registry_bundle(self.temp_dir)

        self.assertEqual(len(bundle.motions), 1)
        self.assertEqual(len(bundle.tasks), 2)
        self.assertEqual(len(bundle.policies), 2)

    def test_upsert_replaces_same_policy_without_duplicate_growth(self) -> None:
        reset_registry_to_examples(self.temp_dir)
        config = load_yaml_config(
            self.temp_dir / "configs" / "policies" / "example_policy_bundle.yaml"
        )

        upsert_registry_item(self.temp_dir, "policies", config)
        upsert_registry_item(self.temp_dir, "policies", config)

        bundle = load_registry_bundle(self.temp_dir)
        policy_ids = [policy["policy_id"] for policy in bundle.policies]
        self.assertEqual(len(bundle.policies), 2)
        self.assertEqual(policy_ids.count("example_base_velocity_policy"), 1)

    def test_upsert_replaces_same_task_without_duplicate_growth(self) -> None:
        reset_registry_to_examples(self.temp_dir)
        config = load_yaml_config(
            self.temp_dir / "configs" / "tasks" / "example_base_velocity_task.yaml"
        )

        upsert_registry_item(self.temp_dir, "tasks", config)
        upsert_registry_item(self.temp_dir, "tasks", config)

        bundle = load_registry_bundle(self.temp_dir)
        task_ids = [task["task_id"] for task in bundle.tasks]
        self.assertEqual(len(bundle.tasks), 2)
        self.assertEqual(task_ids.count("g1_base_velocity_flat"), 1)


if __name__ == "__main__":
    unittest.main()
