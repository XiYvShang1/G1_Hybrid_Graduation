"""Wrapper for unitree_rl_mjlab task registration and execution planning."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class MJLabAdapter:
    repo_root: Path

    @property
    def train_entry(self) -> Path:
        return self.repo_root / "scripts" / "train.py"

    @property
    def play_entry(self) -> Path:
        return self.repo_root / "scripts" / "play.py"

    @property
    def velocity_deploy_config(self) -> Path:
        return (
            self.repo_root
            / "deploy"
            / "robots"
            / "g1_23dof"
            / "config"
            / "policy"
            / "velocity"
            / "v0"
            / "params"
            / "deploy.yaml"
        )

    @staticmethod
    def _missing_paths(paths: list[Path]) -> list[str]:
        return [str(path) for path in paths if not path.exists()]

    def build_base_policy_plan(
        self,
        upstream_task_id: str,
        *,
        python_executable: str = "python3",
        num_envs: int = 128,
    ) -> dict[str, Any]:
        train_command = [
            python_executable,
            str(self.train_entry),
            upstream_task_id,
            f"--env.scene.num-envs={int(num_envs)}",
        ]
        play_command = [
            python_executable,
            str(self.play_entry),
            upstream_task_id,
        ]

        missing = self._missing_paths(
            [self.train_entry, self.play_entry, self.velocity_deploy_config]
        )
        status = "ready" if not missing else "blocked_missing_paths"

        return {
            "adapter": "unitree_rl_mjlab",
            "repo_root": str(self.repo_root),
            "upstream_task_id": upstream_task_id,
            "train_entry": str(self.train_entry),
            "play_entry": str(self.play_entry),
            "velocity_deploy_config": str(self.velocity_deploy_config),
            "train_command": train_command,
            "play_command": play_command,
            "cwd": str(self.repo_root),
            "status": status,
            "missing_paths": missing,
            "note": "wrapper 已生成基础训练/回放命令模板；默认不在 pipeline 中自动重训练。",
        }
