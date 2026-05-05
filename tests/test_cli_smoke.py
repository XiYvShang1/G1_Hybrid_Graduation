"""Smoke tests for CLI entrypoints in local project mode."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class CLISmokeTest(unittest.TestCase):
    def _run(self, *args: str) -> str:
        completed = subprocess.run(
            [sys.executable, "-m", "cli", *args],
            cwd=PROJECT_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError(
                f"command failed: {' '.join(args)}\n"
                f"exit code: {completed.returncode}\n"
                f"output:\n{completed.stdout}"
            )
        return completed.stdout

    def test_status_command(self) -> None:
        output = self._run("status")
        self.assertIn("G1 23DoF 项目状态", output)
        self.assertIn("速度跟踪任务", output)
        self.assertIn("动作跟踪任务", output)

    def test_check_paths_command(self) -> None:
        output = self._run("check-paths")
        self.assertIn("scripts", output)
        self.assertIn("g1_23dof", output)

    def test_prepare_motion_dry_run(self) -> None:
        output = self._run("prepare-motion", "--dry-run")
        self.assertIn("copy", output)
        self.assertIn("example_motion.npz", output)

    def test_training_shortcuts_dry_run(self) -> None:
        velocity = self._run("train-velocity", "--dry-run")
        tracking = self._run("train-tracking", "--dry-run")

        self.assertIn("Unitree-G1-23Dof-Flat", velocity)
        self.assertIn("Unitree-G1-23Dof-Tracking", tracking)
        self.assertIn("example_motion.npz", tracking)

    def test_sim_shortcuts_dry_run(self) -> None:
        build = self._run("build-sim", "--dry-run")
        stack = self._run("sim-stack", "--dry-run")

        self.assertIn("cmake -S simulate", build)
        self.assertIn("unitree_mujoco", stack)
        self.assertIn("g1_ctrl", stack)


if __name__ == "__main__":
    unittest.main()
