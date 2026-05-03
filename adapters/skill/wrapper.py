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
        return self.project_root / "engines" / "base_locomotion"

    @property
    def train_entry(self) -> Path:
        return self.engine_root / "scripts" / "train.py"

    @property
    def export_entry(self) -> Path:
        return self.engine_root / "scripts" / "play.py"

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
        motion_file: str | Path | None = None,
        python_executable: str = "python",
        num_envs: int = 128,
        experiment_name: str = "hybrid_debug",
    ) -> dict[str, Any]:
        resolved_motion_file = str(motion_file or motion_asset_id)
        train_command = [
            python_executable,
            str(self.train_entry),
            task_name,
            "--motion-file",
            resolved_motion_file,
            f"--env.scene.num-envs={int(num_envs)}",
            f"--agent.experiment-name={experiment_name}",
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
            "motion_file": resolved_motion_file,
            "task_name": task_name,
            "train_entry": str(self.train_entry),
            "export_entry": str(self.export_entry),
            "deploy_check_entry": str(self.deploy_check_entry),
            "train_command": train_command,
            "deploy_command": deploy_command,
            "cwd": str(self.engine_root),
            "status": status,
            "missing_paths": missing,
            "note": "Use the mjlab motion-tracking training entrypoint; workflow controls execution.",
        }
