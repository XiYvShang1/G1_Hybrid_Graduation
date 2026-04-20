"""Base locomotion adapter for project-local training plans."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BasePolicyAdapter:
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
    def deploy_handoff_config(self) -> Path:
        return self.project_root / "configs" / "deploy" / "example_deploy_handoff.yaml"

    @staticmethod
    def _missing_paths(paths: list[Path]) -> list[str]:
        return [str(path) for path in paths if not path.exists()]

    def build_base_policy_plan(
        self,
        upstream_task_id: str,
        *,
        python_executable: str = "python",
        num_envs: int = 128,
    ) -> dict[str, Any]:
        train_command = [
            python_executable,
            str(self.train_entry),
            upstream_task_id,
            f"--env.scene.num-envs={int(num_envs)}",
        ]
        export_command = [
            python_executable,
            str(self.export_entry),
            upstream_task_id,
        ]

        missing = self._missing_paths(
            [self.train_entry, self.export_entry, self.deploy_handoff_config]
        )
        status = "ready" if not missing else "blocked_missing_paths"

        return {
            "adapter": "base_domain",
            "project_root": str(self.project_root),
            "engine_root": str(self.engine_root),
            "upstream_task_id": upstream_task_id,
            "train_entry": str(self.train_entry),
            "export_entry": str(self.export_entry),
            "deploy_handoff_config": str(self.deploy_handoff_config),
            "train_command": train_command,
            "export_command": export_command,
            "cwd": str(self.engine_root),
            "status": status,
            "missing_paths": missing,
            "note": "已生成项目内基础策略真实训练/回放命令；默认不自动重训练。",
        }
