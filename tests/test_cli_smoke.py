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
        self.assertIn("项目状态概览", output)
        self.assertIn("动作资产数量", output)

    def test_show_closure_command(self) -> None:
        output = self._run("show-closure")
        self.assertIn("最小闭环报告", output)

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
