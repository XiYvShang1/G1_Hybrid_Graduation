"""G1 23DoF 视频动作到 Mimic 训练数据的项目级流水线。

这个模块只负责“编排”：把 GVHMR、G1 重定向、CSV/NPZ 转换这些后端串起来。
真正的算法实现放在 `motion_pipeline/backends` 和底层 mjlab 训练引擎中。
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENGINE_ROOT = PROJECT_ROOT / "engines" / "base_locomotion"
PIPELINE_ROOT = PROJECT_ROOT / "motion_pipeline"
GVHMR_ROOT = PIPELINE_ROOT / "backends" / "gvhmr"
RETARGET_ROOT = PIPELINE_ROOT / "backends" / "g1_retarget"
SMPL_RETARGET_ROOT = RETARGET_ROOT / "smpl_retarget"


@dataclass(frozen=True)
class RuntimeDefaults:
    """流水线默认运行环境。"""

    tools_python: str = os.environ.get("G1_TOOLS_PYTHON", "python")
    gvhmr_python: str = os.environ.get("G1_GVHMR_PYTHON", "python")
    retarget_python: str = os.environ.get("G1_RETARGET_PYTHON", "python")
    mjlab_python: str = os.environ.get("G1_MJLAB_PYTHON", "python")
    runtime_root: Path = PROJECT_ROOT / "runtime" / "motion_pipeline"


def windows_path_to_wsl(raw_path: str) -> str:
    """把 Windows 绝对路径转成 WSL /mnt/<drive>/... 路径。"""
    path = PureWindowsPath(raw_path)
    if not path.drive:
        return raw_path
    drive = path.drive.rstrip(":").lower()
    parts = [part for part in path.parts[1:] if part not in {"\\", "/"}]
    return "/mnt/" + drive + "/" + "/".join(parts)


def arg_for_shell(arg: object) -> str:
    """把命令参数转成目标 shell 可识别路径。"""
    raw = str(arg)
    if PureWindowsPath(raw).drive:
        return windows_path_to_wsl(raw)
    return raw


def quote_shell_arg(arg: object) -> str:
    """生成 bash -lc 中安全使用的参数。"""
    return shlex.quote(arg_for_shell(arg))


def resolve_project_path(path: Path) -> Path:
    """把相对路径固定到项目根目录。"""
    if path.is_absolute():
        return path
    return (PROJECT_ROOT / path).resolve()


def build_process_command(cwd: Path, args: list[object]) -> list[str]:
    """根据 Windows/WSL 边界生成实际进程命令。"""
    command = [str(arg) for arg in args]
    if sys.platform.startswith("win") and command and command[0].startswith("/"):
        wsl_cwd = windows_path_to_wsl(str(cwd))
        wsl_command = " ".join(quote_shell_arg(arg) for arg in command)
        return ["wsl.exe", "bash", "-lc", f"cd {shlex.quote(wsl_cwd)} && {wsl_command}"]
    return command


def run_command(cwd: Path, args: list[object], *, dry_run: bool = False) -> int:
    """运行命令；dry-run 只打印实际命令。"""
    command = build_process_command(cwd, args)
    if dry_run:
        print(subprocess.list2cmdline(command))
        return 0
    completed = subprocess.run(command, cwd=cwd if command[0] != "wsl.exe" else None)
    return completed.returncode


def retarget_pythonpath_prefix() -> str:
    """G1 重定向后端需要把 sibling packages 加到 PYTHONPATH。"""
    root = quote_shell_arg(RETARGET_ROOT)
    return f"PYTHONPATH={root}:$PYTHONPATH"


def video_to_smpl_commands(
    *,
    video: Path,
    output: Path,
    output_root: Path,
    python: str,
    person: int = 0,
    static_cam: bool = False,
    use_dpvo: bool = False,
    f_mm: int | None = None,
    fps: int = 30,
    frame: str = "global",
    skip_demo: bool = False,
    results: Path | None = None,
) -> list[list[object]]:
    """生成 MP4 -> GVHMR -> 标准 SMPL npz 的命令序列。"""
    video = resolve_project_path(video)
    output = resolve_project_path(output)
    output_root = resolve_project_path(output_root)
    results_path = resolve_project_path(results) if results else output_root / video.stem / "hmr4d_results.pt"

    commands: list[list[object]] = []
    if not skip_demo:
        demo_command: list[object] = [
            python,
            GVHMR_ROOT / "tools" / "demo" / "demo.py",
            "--video",
            video,
            "--output_root",
            output_root,
            "--person",
            person,
        ]
        if static_cam:
            demo_command.append("--static_cam")
        if use_dpvo:
            demo_command.append("--use_dpvo")
        if f_mm is not None:
            demo_command.append(f"--f_mm={f_mm}")
        commands.append(demo_command)

    commands.append(
        [
            python,
            PIPELINE_ROOT / "converters" / "gvhmr_to_smpl.py",
            results_path,
            output,
            "--fps",
            fps,
            "--frame",
            frame,
        ]
    )
    return commands


def retarget_motion_command(*, motion_folder: Path, python: str, correct: bool = False, extra: list[str] | None = None) -> list[object]:
    """生成 SMPL -> G1 retarget pkl 命令。"""
    script = SMPL_RETARGET_ROOT / "mink_retarget" / "convert_fit_motion.py"
    command_parts = [
        quote_shell_arg(python),
        quote_shell_arg(script),
        quote_shell_arg(resolve_project_path(motion_folder)),
    ]
    if correct:
        command_parts.append("--correct")
    command_parts.extend(shlex.quote(item) for item in (extra or []))
    return ["/bin/bash", "-lc", f"{retarget_pythonpath_prefix()} {' '.join(command_parts)}"]


def retarget_motion_phc_command(*, motion_folder: Path, python: str, robot: str, extra: list[str] | None = None) -> list[object]:
    """生成 PHC 后端重定向命令。"""
    script = SMPL_RETARGET_ROOT / "phc_retarget" / "fit_smpl_motion.py"
    command_parts = [
        quote_shell_arg(python),
        quote_shell_arg(script),
        f"robot={shlex.quote(robot)}",
        f"+motion={quote_shell_arg(resolve_project_path(motion_folder))}",
    ]
    command_parts.extend(shlex.quote(item) for item in (extra or []))
    return ["/bin/bash", "-lc", f"{retarget_pythonpath_prefix()} {' '.join(command_parts)}"]


def filter_smpl_motion_command(*, motion_folder: Path, python: str, convert_rot: str, extra: list[str] | None = None) -> list[object]:
    """生成 SMPL 动作过滤命令。"""
    script = SMPL_RETARGET_ROOT / "motion_filter" / "utils" / "motion_filter.py"
    command_parts = [
        quote_shell_arg(python),
        quote_shell_arg(script),
        "--folder",
        quote_shell_arg(resolve_project_path(motion_folder)),
        "--convert_rot",
        shlex.quote(convert_rot),
    ]
    command_parts.extend(shlex.quote(item) for item in (extra or []))
    return ["/bin/bash", "-lc", f"{retarget_pythonpath_prefix()} {' '.join(command_parts)}"]


def pkl_to_csv_command(*, input_path: Path, output_path: Path, robot: str, motion_key: str | None = None) -> list[object]:
    """生成 retarget pkl -> mjlab CSV 命令。"""
    command: list[object] = [
        RuntimeDefaults().tools_python,
        PIPELINE_ROOT / "converters" / "pkl_to_csv.py",
        resolve_project_path(input_path),
        resolve_project_path(output_path),
        "--robot",
        robot,
    ]
    if motion_key:
        command.extend(["--motion-key", motion_key])
    return command


def csv_to_npz_command(
    *,
    input_path: Path,
    output_path: Path,
    python: str,
    robot: str,
    input_fps: float,
    output_fps: float,
    device: str,
    render: bool = False,
) -> list[object]:
    """生成 mjlab CSV -> tracking NPZ 命令。"""
    command: list[object] = [
        python,
        ENGINE_ROOT / "scripts" / "csv_to_npz.py",
        robot,
        resolve_project_path(input_path),
        resolve_project_path(output_path),
        "--input-fps",
        input_fps,
        "--output-fps",
        output_fps,
        "--device",
        device,
    ]
    if render:
        command.append("--render")
    return command
