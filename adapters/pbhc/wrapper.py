"""Wrapper for PBHC training and deploy handoff planning."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PBHCAdapter:
    repo_root: Path

    @property
    def train_entry(self) -> Path:
        return self.repo_root / "humanoidverse" / "train_agent.py"

    @property
    def urci_entry(self) -> Path:
        return self.repo_root / "humanoidverse" / "urci.py"

    @property
    def deploy_entry(self) -> Path:
        return self.repo_root / "DemoTest" / "new_mjlab_real" / "deploy_real_new.py"

    @staticmethod
    def _missing_paths(paths: list[Path]) -> list[str]:
        return [str(path) for path in paths if not path.exists()]

    def build_skill_policy_plan(
        self,
        motion_asset_id: str,
        task_name: str,
        *,
        python_executable: str = "python3",
        num_envs: int = 128,
        experiment_name: str = "hybrid_debug",
    ) -> dict[str, Any]:
        train_command = [
            python_executable,
            str(self.train_entry),
            "+simulator=isaacgym",
            "+exp=motion_tracking",
            "+terrain=terrain_locomotion_plane",
            "project_name=MotionTracking",
            f"num_envs={int(num_envs)}",
            "+obs=motion_tracking/benchmark",
            "+robot=g1/g1_23dof_lock_wrist",
            "+domain_rand=dr_nil",
            "+rewards=motion_tracking/main",
            f"experiment_name={experiment_name}",
            "seed=1",
            "+device=cuda:0",
        ]

        deploy_command = [
            python_executable,
            str(self.deploy_entry),
            "--help",
        ]

        missing = self._missing_paths([self.train_entry, self.urci_entry, self.deploy_entry])
        status = "ready" if not missing else "blocked_missing_paths"

        return {
            "adapter": "skill_domain",
            "repo_root": str(self.repo_root),
            "motion_asset_id": motion_asset_id,
            "task_name": task_name,
            "train_entry": str(self.train_entry),
            "urci_entry": str(self.urci_entry),
            "deploy_entry": str(self.deploy_entry),
            "train_command": train_command,
            "deploy_command": deploy_command,
            "cwd": str(self.repo_root),
            "status": status,
            "missing_paths": missing,
            "note": "wrapper 已生成技能训练与部署检查命令模板；真实执行由 workflow 阶段控制。",
        }
