"""Config-driven command orchestration for project-local G1 hybrid stages."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
import subprocess
import sys
import os
import shlex
from typing import Any

from adapters.base import BasePolicyAdapter
from adapters.motion import MotionAssetAdapter
from adapters.skill import SkillPolicyAdapter
from path_utils import resolve_workspace_path
from registry_manager import load_yaml_config


@dataclass(frozen=True)
class StagePlan:
    name: str
    command: list[str]
    cwd: Path
    execute_enabled: bool
    note: str
    expected_output: Path | None = None
    precheck_command: list[str] | None = None


@dataclass(frozen=True)
class StageResult:
    name: str
    status: str
    cwd: str
    command: str
    note: str
    exit_code: int | None
    expected_output: str | None


class WorkflowRunner:
    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()
        self.runtime_dir = self.project_root / "runtime" / "orchestration"
        self.runtime_dir.mkdir(parents=True, exist_ok=True)

        self.motion = MotionAssetAdapter(self.project_root)
        self.base = BasePolicyAdapter(self.project_root)
        self.skill = SkillPolicyAdapter(self.project_root)

    def load_workflow(self, config_path: Path) -> dict[str, Any]:
        return load_yaml_config(config_path)

    @staticmethod
    def _python_has_modules(python_executable: str, module_names: list[str]) -> bool:
        try:
            script = "\n".join([f"import {module_name}" for module_name in module_names])
            completed = subprocess.run(
                [python_executable, "-c", script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except OSError:
            return False
        return completed.returncode == 0

    def _python_executable(self, workflow_cfg: dict[str, Any]) -> str:
        configured = workflow_cfg.get("python_executable", "auto")
        if configured != "auto":
            return str(configured)

        required_modules = ["numpy", "yaml"]

        candidates: list[str] = []
        conda_prefix = os.environ.get("CONDA_PREFIX")
        if conda_prefix:
            candidates.append(str(Path(conda_prefix) / "bin" / "python"))

        conda_envs_root = Path.home() / "miniconda3" / "envs"
        if conda_envs_root.exists():
            candidates.extend(
                str(path)
                for path in sorted(conda_envs_root.glob("*/bin/python"))
            )

        candidates.extend([sys.executable, "/usr/bin/python3"])

        seen: set[str] = set()
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            if self._python_has_modules(candidate, required_modules):
                return candidate

        return sys.executable

    def _stage_python_executable(
        self, workflow_cfg: dict[str, Any], stage_cfg: dict[str, Any]
    ) -> str:
        configured = stage_cfg.get("python_executable")
        if configured:
            if str(configured).startswith("/"):
                return str(configured)
            return str(resolve_workspace_path(self.project_root, str(configured)))
        return self._python_executable(workflow_cfg)

    @staticmethod
    def _windows_path_to_wsl(raw_path: str) -> str:
        windows_path = PureWindowsPath(raw_path)
        if not windows_path.drive:
            return raw_path
        drive = windows_path.drive.rstrip(":").lower()
        parts = [part for part in windows_path.parts[1:] if part not in {"\\", "/"}]
        return "/mnt/" + drive + "/" + "/".join(parts)

    def _stage_command(
        self, python_executable: str, cwd: Path, args: list[str]
    ) -> list[str]:
        if os.name == "nt" and python_executable.startswith("/"):
            wsl_args = [
                self._windows_path_to_wsl(arg)
                if PureWindowsPath(arg).drive
                else arg
                for arg in [python_executable, *args]
            ]
            wsl_cwd = self._windows_path_to_wsl(str(cwd))
            shell_command = (
                f"cd {shlex.quote(wsl_cwd)} && "
                + " ".join(shlex.quote(arg) for arg in wsl_args)
            )
            return ["wsl.exe", "bash", "-lc", shell_command]
        return [python_executable, *args]

    def _motion_output_path(self, motion_cfg: dict[str, Any]) -> Path:
        if "output_file" in motion_cfg:
            output_file = resolve_workspace_path(
                self.project_root, str(motion_cfg["output_file"])
            )
            output_file.parent.mkdir(parents=True, exist_ok=True)
            return output_file

        source = Path(str(motion_cfg["source_pkl"]))
        source_name = source.stem
        fix_part = str(motion_cfg.get("fix_part", "lower"))
        split_index = int(motion_cfg.get("split_index", 12))
        output_dir = (self.project_root / str(motion_cfg["output_dir"])).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        suffix = f"_fix-{fix_part}"
        if fix_part in {"lower", "upper"}:
            suffix += f"_split-{split_index}"
        elif fix_part == "none":
            suffix = "_unmodified"

        return output_dir / f"{source_name}{suffix}.pkl"

    def build_stage_plans(
        self,
        workflow_cfg: dict[str, Any],
        selected_stages: set[str] | None = None,
    ) -> list[StagePlan]:
        stages: list[StagePlan] = []
        selected = selected_stages or {"motion", "base", "skill"}

        motion_cfg = workflow_cfg.get("motion", {})
        motion_python = self._stage_python_executable(workflow_cfg, motion_cfg)
        motion_output = self._motion_output_path(motion_cfg)
        motion_source_key = "source_file" if "source_file" in motion_cfg else "source_pkl"
        motion_source = resolve_workspace_path(
            self.project_root, str(motion_cfg[motion_source_key])
        )
        if "motion" in selected and motion_cfg.get("enabled", True):
            stages.append(
                StagePlan(
                    name="motion",
                    command=self._stage_command(
                        motion_python,
                        self.project_root,
                        [
                            str(self.motion.processor_script),
                            str(motion_source),
                            "--output",
                            str(motion_output),
                            "--fix-part",
                            str(motion_cfg.get("fix_part", "lower")),
                            "--split-index",
                            str(int(motion_cfg.get("split_index", 12))),
                        ],
                    ),
                    cwd=self.project_root,
                    execute_enabled=bool(motion_cfg.get("execute", True)),
                    note="执行动作资产处理脚本生成项目 runtime motion asset",
                    expected_output=motion_output,
                )
            )

        base_cfg = workflow_cfg.get("base", {})
        base_python = self._stage_python_executable(workflow_cfg, base_cfg)
        if "base" in selected and base_cfg.get("enabled", True):
            task_id = str(base_cfg.get("task_id", "Unitree-G1-23Dof-Flat"))
            num_envs = int(base_cfg.get("num_envs", 128))

            stages.append(
                StagePlan(
                    name="base",
                    command=self._stage_command(
                        base_python,
                        self.base.engine_root,
                        [
                            str(self.base.train_entry),
                            task_id,
                            f"--env.scene.num-envs={num_envs}",
                        ],
                    ),
                    cwd=self.base.engine_root,
                    execute_enabled=bool(base_cfg.get("execute", False)),
                    note="执行基础策略训练入口命令",
                    expected_output=None,
                    precheck_command=None,
                )
            )

        skill_cfg = workflow_cfg.get("skill", {})
        skill_python = self._stage_python_executable(workflow_cfg, skill_cfg)
        if "skill" in selected and skill_cfg.get("enabled", True):
            skill_mode = str(skill_cfg.get("mode", "train"))
            motion_file_mode = str(
                skill_cfg.get("motion_file_mode", "from_motion_stage")
            )
            if motion_file_mode == "from_motion_stage":
                motion_file = motion_output
            else:
                motion_file = resolve_workspace_path(
                    self.project_root, str(skill_cfg["motion_file"])
                )

            if skill_mode == "deploy_check":
                deploy_config = resolve_workspace_path(
                    self.project_root, str(skill_cfg["deploy_config"])
                )
                stages.append(
                    StagePlan(
                        name="skill",
                        command=[
                            skill_python,
                            str(self.skill.deploy_check_entry),
                            "--policy-id",
                            str(skill_cfg.get("policy_id", "example_skill_policy")),
                            "--motion",
                            str(motion_file),
                            "--config",
                            str(deploy_config),
                        ]
                        + (
                            ["--expect-standard23"]
                            if bool(skill_cfg.get("expect_standard23", False))
                            else []
                        ),
                        cwd=self.project_root,
                        execute_enabled=bool(skill_cfg.get("execute", False)),
                        note="执行技能域 deploy consistency check 验证 motion 与 deploy config 的一致性",
                        expected_output=None,
                        precheck_command=None,
                    )
                )
            else:
                task_id = str(skill_cfg.get("task_id", "Unitree-G1-23Dof-Tracking"))
                stages.append(
                    StagePlan(
                        name="skill",
                        command=self._stage_command(
                            skill_python,
                            self.skill.engine_root,
                            [
                                str(self.skill.train_entry),
                                task_id,
                                "--motion-file",
                                str(motion_file),
                                f"--env.scene.num-envs={int(skill_cfg.get('num_envs', 128))}",
                                f"--agent.experiment-name={skill_cfg.get('experiment_name', 'hybrid_debug')}",
                            ],
                        ),
                        cwd=self.skill.engine_root,
                        execute_enabled=bool(skill_cfg.get("execute", False)),
                        note=f"执行 mjlab 动作跟踪训练入口 | task_id={task_id} | motion_file={motion_file}",
                        expected_output=None,
                        precheck_command=None,
                    )
                )

        return stages

    def run(
        self,
        workflow_cfg: dict[str, Any],
        execute: bool,
        selected_stages: set[str] | None = None,
    ) -> list[StageResult]:
        plans = self.build_stage_plans(workflow_cfg, selected_stages)
        results: list[StageResult] = []

        for plan in plans:
            if not execute:
                results.append(
                    StageResult(
                        name=plan.name,
                        status="planned",
                        cwd=str(plan.cwd),
                        command=subprocess.list2cmdline(plan.command),
                        note=plan.note,
                        exit_code=None,
                        expected_output=str(plan.expected_output)
                        if plan.expected_output
                        else None,
                    )
                )
                continue

            if not plan.execute_enabled:
                blocked_note = plan.note
                if "blocked:" in plan.note:
                    blocked_note = plan.note
                results.append(
                    StageResult(
                        name=plan.name,
                        status="blocked" if "blocked:" in plan.note else "skipped",
                        cwd=str(plan.cwd),
                        command=subprocess.list2cmdline(plan.command),
                        note=(
                            blocked_note
                            if "blocked:" in plan.note
                            else f"配置中 execute=false，未自动执行。{plan.note}"
                        ),
                        exit_code=None,
                        expected_output=str(plan.expected_output)
                        if plan.expected_output
                        else None,
                    )
                )
                continue

            completed = subprocess.run(
                plan.command,
                cwd=plan.cwd,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                check=False,
            )
            output_path = self.runtime_dir / f"{plan.name}_latest.log"
            log_chunks = []

            if plan.precheck_command is not None:
                precheck = subprocess.run(
                    plan.precheck_command,
                    cwd=plan.cwd,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                    check=False,
                )
                log_chunks.append("[PRECHECK]\n" + precheck.stdout)
                if precheck.returncode != 0:
                    output_path.write_text("\n\n".join(log_chunks), encoding="utf-8")
                    results.append(
                        StageResult(
                            name=plan.name,
                            status="failed",
                            cwd=str(plan.cwd),
                            command=subprocess.list2cmdline(plan.command),
                            note=plan.note + f" | precheck_failed | log={output_path}",
                            exit_code=precheck.returncode,
                            expected_output=str(plan.expected_output)
                            if plan.expected_output
                            else None,
                        )
                    )
                    continue

            log_chunks.append("[COMMAND]\n" + completed.stdout)
            output_path.write_text("\n\n".join(log_chunks), encoding="utf-8")

            status = "success" if completed.returncode == 0 else "failed"
            if (
                status == "success"
                and plan.expected_output is not None
                and not plan.expected_output.exists()
            ):
                status = "failed"

            note = plan.note + f" | log={output_path}"
            if plan.expected_output is not None:
                note += f" | expected_output={plan.expected_output}"

            results.append(
                StageResult(
                    name=plan.name,
                    status=status,
                    cwd=str(plan.cwd),
                    command=subprocess.list2cmdline(plan.command),
                    note=note,
                    exit_code=completed.returncode,
                    expected_output=str(plan.expected_output)
                    if plan.expected_output
                    else None,
                )
            )

        report_path = self.runtime_dir / "last_run_report.txt"
        report_path.write_text(self.format_results(results), encoding="utf-8")
        return results

    @staticmethod
    def format_results(results: list[StageResult]) -> str:
        lines = ["Hybrid workflow execution report", "=" * 32]
        for result in results:
            lines.extend(
                [
                    f"stage: {result.name}",
                    f"status: {result.status}",
                    f"cwd: {result.cwd}",
                    f"command: {result.command}",
                    f"note: {result.note}",
                    f"exit_code: {result.exit_code}",
                    f"expected_output: {result.expected_output}",
                    "-" * 32,
                ]
            )
        return "\n".join(lines)
