"""Wrapper for GVHMR2PBHC motion conversion utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GVHMR2PBHCAdapter:
    repo_root: Path

    @property
    def converter_script(self) -> Path:
        return self.repo_root / "Converter_V4.py"

    @property
    def retarget_script(self) -> Path:
        return self.repo_root / "convert_fit_motion_V2.py"

    @property
    def modify_motion_script(self) -> Path:
        return self.repo_root / "modify_motion.py"

    @staticmethod
    def _missing_paths(paths: list[Path]) -> list[str]:
        return [str(path) for path in paths if not path.exists()]

    def build_motion_asset_plan(
        self,
        source_path: Path,
        target_path: Path,
        *,
        python_executable: str = "python3",
        fix_part: str = "lower",
        split_index: int = 12,
    ) -> dict[str, Any]:
        source_path = source_path.resolve()
        target_path = target_path.resolve()

        command = [
            python_executable,
            str(self.modify_motion_script),
            str(source_path),
            "--output-folder",
            str(target_path.parent),
            "--fix-part",
            str(fix_part),
            "--split-index",
            str(int(split_index)),
        ]

        missing = self._missing_paths(
            [self.modify_motion_script, self.converter_script, self.retarget_script, source_path]
        )
        status = "ready" if not missing else "blocked_missing_paths"

        return {
            "adapter": "GVHMR2PBHC",
            "repo_root": str(self.repo_root),
            "source_path": str(source_path),
            "target_path": str(target_path),
            "converter_script": str(self.converter_script),
            "retarget_script": str(self.retarget_script),
            "modify_motion_script": str(self.modify_motion_script),
            "command": command,
            "cwd": str(self.repo_root),
            "status": status,
            "missing_paths": missing,
            "note": "wrapper 已生成可执行命令；默认由 workflow/CLI 在受控条件下执行。",
        }
