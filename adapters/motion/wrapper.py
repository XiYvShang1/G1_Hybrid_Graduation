"""Motion asset processing adapter for project-local utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class MotionAssetAdapter:
    project_root: Path

    @property
    def processor_script(self) -> Path:
        return self.project_root / "pipelines" / "process_motion_asset.py"

    @staticmethod
    def _missing_paths(paths: list[Path]) -> list[str]:
        return [str(path) for path in paths if not path.exists()]

    def build_motion_asset_plan(
        self,
        source_path: Path,
        target_path: Path,
        *,
        python_executable: str = "python",
        fix_part: str = "lower",
        split_index: int = 12,
    ) -> dict[str, Any]:
        source_path = source_path.resolve()
        target_path = target_path.resolve()

        command = [
            python_executable,
            str(self.processor_script),
            str(source_path),
            "--output",
            str(target_path),
            "--fix-part",
            str(fix_part),
            "--split-index",
            str(int(split_index)),
        ]

        missing = self._missing_paths([self.processor_script, source_path])
        status = "ready" if not missing else "blocked_missing_paths"

        return {
            "adapter": "motion_domain",
            "project_root": str(self.project_root),
            "source_path": str(source_path),
            "target_path": str(target_path),
            "processor_script": str(self.processor_script),
            "command": command,
            "cwd": str(self.project_root),
            "status": status,
            "missing_paths": missing,
            "note": "已生成项目内动作资产处理命令；默认由 workflow/CLI 在受控条件下执行。",
        }
