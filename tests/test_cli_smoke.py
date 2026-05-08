"""Smoke tests for CLI entrypoints in local project mode."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pickle


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

    def assert_no_workspace_absolute_path(self, output: str) -> None:
        self.assertNotIn(str(PROJECT_ROOT), output)
        self.assertNotIn(str(PROJECT_ROOT).replace("\\", "/"), output)

    def test_status_command(self) -> None:
        output = self._run("status")
        self.assertIn("G1 23DoF 项目状态", output)
        self.assertIn("23DoF 部署层", output)
        self.assertIn("29DoF 部署层", output)
        self.assertIn("速度跟踪任务", output)
        self.assertIn("动作跟踪任务", output)

    def test_check_paths_command(self) -> None:
        output = self._run("check-paths")
        self.assert_no_workspace_absolute_path(output)
        self.assertIn("scripts", output)
        self.assertIn("g1_23dof", output)
        self.assertIn("g1_29dof", output)

    def test_prepare_motion_dry_run(self) -> None:
        output = self._run("prepare-motion", "--dry-run")
        self.assertIn("copy", output)
        self.assertIn("example_motion.npz", output)

    def test_training_shortcuts_dry_run(self) -> None:
        velocity = self._run("train-velocity", "--dry-run")
        tracking = self._run("train-tracking", "--dry-run")
        csv_to_npz = self._run("csv-to-npz", "runtime/example_motion/example_motion.csv", "--dry-run")
        self.assert_no_workspace_absolute_path(velocity)
        self.assert_no_workspace_absolute_path(tracking)
        self.assert_no_workspace_absolute_path(csv_to_npz)

        self.assertIn("Unitree-G1-23Dof-Flat", velocity)
        self.assertIn("Unitree-G1-23Dof-Tracking", tracking)
        self.assertIn("example_motion.npz", tracking)
        self.assertIn("csv_to_npz.py", csv_to_npz)
        self.assertIn("g1_23dof", csv_to_npz)

        low_cost_tracking = self._run(
            "train-tracking",
            "--num-envs",
            "1",
            "--max-iterations",
            "200",
            "--motion-file",
            "runtime/example_motion/example_motion.npz",
            "--dry-run",
        )
        self.assertIn("--env.scene.num-envs=1", low_cost_tracking)
        self.assertIn("--agent.max-iterations=200", low_cost_tracking)
        self.assertIn("example_motion.npz", low_cost_tracking)

        native_override = self._run(
            "train-tracking",
            "--num-envs",
            "1",
            "--motion-file",
            "runtime/example_motion/example_motion.npz",
            "--agent.save-interval=50",
            "--env.commands.motion.sampling-mode=start",
            "--dry-run",
        )
        self.assertIn("--agent.save-interval=50", native_override)
        self.assertIn("--env.commands.motion.sampling-mode=start", native_override)

    def test_pkl_to_csv_conversion(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "motion.pkl"
            output_path = temp_path / "motion.csv"
            frames = 4
            payload = {
                "demo": {
                    "root_trans_offset": np.zeros((frames, 3), dtype=np.float32),
                    "root_rot": np.tile(np.array([[0.0, 0.0, 0.0, 1.0]], dtype=np.float32), (frames, 1)),
                    "dof": np.zeros((frames, 23), dtype=np.float32),
                    "fps": 30,
                }
            }
            with input_path.open("wb") as file:
                pickle.dump(payload, file)

            output = self._run("pkl-to-csv", str(input_path), "--output", str(output_path))

            self.assertIn("frames=4", output)
            converted = np.loadtxt(output_path, delimiter=",")
            self.assertEqual(converted.shape, (frames, 30))

    def test_sim_shortcuts_dry_run(self) -> None:
        velocity_play = self._run("play-velocity", "--agent", "zero", "--viewer", "viser", "--device", "cpu", "--dry-run")
        tracking_play = self._run(
            "play-tracking",
            "--agent",
            "zero",
            "--motion-file",
            "runtime/example_motion/example_motion.npz",
            "--viewer",
            "viser",
            "--device",
            "cpu",
            "--no-terminations",
            "--dry-run",
        )
        build = self._run("build-23dof-sim", "--dry-run")
        stack = self._run("sim-23dof-stack", "--dry-run")
        sim_29dof = self._run("sim-29dof-mujoco", "--dry-run")
        sim_29dof_viser = self._run(
            "sim-29dof-viser",
            "simulation_dt=0.005",
            "control_decimation=4",
            "render_fps=20",
            "--dry-run",
        )

        self.assertIn("--viewer=viser", velocity_play)
        self.assertIn("--device=cpu", velocity_play)
        self.assertIn("--viewer=viser", tracking_play)
        self.assertIn("--device=cpu", tracking_play)
        self.assertIn("--no-terminations=True", tracking_play)

        onnx_play = self._run(
            "play-onnx",
            "--onnx-file",
            "engines/base_locomotion/deploy/robots/g1_23dof/config/policy/velocity/v0/exported/policy.onnx",
            "--device",
            "cpu",
            "--viewer",
            "viser",
            "--dry-run",
        )
        self.assertIn("play_onnx.py", onnx_play)
        self.assertIn("deploy/robots/g1_23dof/config/policy/velocity/v0/exported/policy.onnx", onnx_play)
        self.assertIn("--device=cpu", onnx_play)
        self.assertIn("--viewer=viser", onnx_play)

        self.assertIn("cmake -S simulate", build)
        self.assertIn("unitree_mujoco", stack)
        self.assertIn("g1_ctrl", stack)
        self.assertIn("deploy_mujoco.py", sim_29dof)
        self.assertIn("g1_29dof", sim_29dof)
        self.assertIn("deploy_mujoco_viser.py", sim_29dof_viser)
        self.assertIn("simulation_dt=0.005", sim_29dof_viser)
        self.assertIn("control_decimation=4", sim_29dof_viser)

    def test_retarget_shortcuts_dry_run(self) -> None:
        video = self._run("video-to-smpl", "runtime/example_motion/input.mp4", "--person", "1", "--dry-run")
        pipeline = self._run("motion-pipeline", "runtime/example_motion/input.mp4", "--name", "demo", "--person", "1", "--dry-run")
        mink = self._run("retarget-motion", "runtime/example_motion", "--dry-run")
        phc = self._run("retarget-motion-phc", "runtime/example_motion", "--dry-run")
        motion_filter = self._run("filter-smpl-motion", "runtime/example_motion", "--dry-run")
        self.assert_no_workspace_absolute_path(video)
        self.assert_no_workspace_absolute_path(pipeline)

        self.assertIn("demo.py", video)
        self.assertIn("gvhmr_to_smpl.py", video)
        self.assertIn("--person 1", video)
        self.assertIn("case_root=", pipeline)
        self.assertIn("motion_pipeline", pipeline)
        self.assertIn("demo_g1.npz", pipeline)
        self.assertIn("convert_fit_motion.py", mink)
        self.assertIn("fit_smpl_motion.py", phc)
        self.assertIn("motion_filter.py", motion_filter)


if __name__ == "__main__":
    unittest.main()
