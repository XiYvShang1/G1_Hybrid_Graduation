"""Skill policy adapter for project-local training and handoff checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SkillPolicyAdapter:
    project_root: Path

    @property
    def engine_root(self) -> Path:
        return self.project_root / "engines" / "skill_tracking"

    @property
    def train_entry(self) -> Path:
        return self.engine_root / "humanoidverse" / "train_agent.py"

    @property
    def export_entry(self) -> Path:
        return self.engine_root / "humanoidverse" / "urci.py"

    @property
    def deploy_check_entry(self) -> Path:
        return self.project_root / "pipelines" / "validate_deploy_handoff.py"

    @staticmethod
    def _missing_paths(paths: list[Path]) -> list[str]:
        return [str(path) for path in paths if not path.exists()]

    def build_skill_policy_plan(
        self,
        motion_asset_id: str,
        task_name: str,
        *,
        python_executable: str = "python",
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
            str(self.deploy_check_entry),
            "--policy-id",
            "example_skill_policy",
        ]

        missing = self._missing_paths(
            [self.train_entry, self.export_entry, self.deploy_check_entry]
        )
        status = "ready" if not missing else "blocked_missing_paths"

        return {
            "adapter": "skill_domain",
            "project_root": str(self.project_root),
            "engine_root": str(self.engine_root),
            "motion_asset_id": motion_asset_id,
            "task_name": task_name,
            "train_entry": str(self.train_entry),
            "export_entry": str(self.export_entry),
            "deploy_check_entry": str(self.deploy_check_entry),
            "train_command": train_command,
            "deploy_command": deploy_command,
            "cwd": str(self.engine_root),
            "status": status,
            "missing_paths": missing,
            "note": "已生成项目内技能动作跟踪真实训练与部署检查命令；真实执行由 workflow 阶段控制。",
        }
