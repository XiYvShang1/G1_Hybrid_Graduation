"""G1 23DoF 项目的统一命令行入口。

这个文件负责把用户常用动作收敛成几条根目录命令：
- 准备动作文件：prepare-motion
- 启动训练：train-velocity / train-tracking
- 回放策略：play-velocity / play-tracking / play-onnx
- 部署侧仿真：23DoF build/sim/deploy，以及 29DoF 已训练策略的 MuJoCo 演示

真正的训练代码仍在 engines/base_locomotion/scripts 里；这里主要做路径整理、
Windows/WSL 命令转换和参数拼接。
"""

from __future__ import annotations

import argparse
import os
import shutil
import shlex
import subprocess
import sys
from pathlib import Path, PureWindowsPath

from motion_pipeline import pipeline as motion_pipeline


PROJECT_ROOT = Path(__file__).resolve().parent
ENGINE_ROOT = PROJECT_ROOT / "engines" / "base_locomotion"
DEPLOYMENTS_ROOT = PROJECT_ROOT / "deployments"
DEPLOY_23DOF_ROOT = ENGINE_ROOT / "deploy" / "robots" / "g1_23dof"
DEPLOY_29DOF_ROOT = DEPLOYMENTS_ROOT / "g1_29dof"
MOTION_PIPELINE_ROOT = motion_pipeline.PIPELINE_ROOT
MOTION_RETARGET_ROOT = motion_pipeline.RETARGET_ROOT
SMPL_RETARGET_ROOT = motion_pipeline.SMPL_RETARGET_ROOT
GVHMR_ROOT = motion_pipeline.GVHMR_ROOT

DEFAULT_MJLAB_PYTHON = os.environ.get("G1_MJLAB_PYTHON", "python")
DEFAULT_29DOF_PYTHON = os.environ.get("G1_29DOF_PYTHON", "python")
DEFAULT_RETARGET_PYTHON = os.environ.get("G1_RETARGET_PYTHON", "python")
DEFAULT_GVHMR_PYTHON = os.environ.get("G1_GVHMR_PYTHON", "python")
DEFAULT_VELOCITY_TASK = "Unitree-G1-23Dof-Flat"
DEFAULT_TRACKING_TASK = "Unitree-G1-23Dof-Tracking"
DEFAULT_SOURCE_MOTION = ENGINE_ROOT / "src" / "assets" / "motions" / "g1_23dof" / "jilejingtu.npz"
DEFAULT_RUNTIME_MOTION = PROJECT_ROOT / "runtime" / "example_motion" / "example_motion.npz"
DEFAULT_RUNTIME_CSV = PROJECT_ROOT / "runtime" / "example_motion" / "example_motion.csv"


def _windows_path_to_wsl(raw_path: str) -> str:
    """把 Windows 绝对路径转换成 WSL 可识别的 /mnt/<drive>/... 路径。"""
    path = PureWindowsPath(raw_path)
    if not path.drive:
        return raw_path
    drive = path.drive.rstrip(":").lower()
    parts = [part for part in path.parts[1:] if part not in {"\\", "/"}]
    return "/mnt/" + drive + "/" + "/".join(parts)


def _arg_for_shell(arg: object) -> str:
    """把单个命令参数转换成目标 shell 需要的路径形式。"""
    raw = str(arg)
    if os.name == "nt" and PureWindowsPath(raw).drive:
        return _windows_path_to_wsl(raw)
    return raw


def _resolve_user_path(path: Path) -> Path:
    """把用户输入的相对路径固定到项目根目录，避免 Windows/WSL 工作目录不一致。"""
    if path.is_absolute():
        return path
    return (PROJECT_ROOT / path).resolve()


def _quote_shell_arg(arg: object) -> str:
    """把参数转换成适合 bash -lc 字符串的安全形式。"""
    return shlex.quote(_arg_for_shell(arg))


def _retarget_pythonpath_prefix() -> str:
    """动作重定向工具依赖 sibling packages，运行时需要把工具根目录加入 PYTHONPATH。"""
    root = _quote_shell_arg(MOTION_RETARGET_ROOT)
    return f"PYTHONPATH={root}:$PYTHONPATH"


def _build_process_command(cwd: Path, args: list[object]) -> list[str]:
    """根据当前系统生成最终 subprocess 命令。

    在 Windows 上，如果要执行的是 Linux 绝对路径命令，例如 /bin/bash 或
    WSL 中的 Python，就自动包一层 wsl.exe bash -lc，并把工作目录切到
    WSL 路径。这样用户在 Windows 根目录里也能直接启动 Linux 训练环境。
    """
    command = [str(arg) for arg in args]
    if os.name == "nt" and command and command[0].startswith("/"):
        wsl_cwd = _windows_path_to_wsl(str(cwd))
        wsl_command = " ".join(shlex.quote(_arg_for_shell(arg)) for arg in command)
        return ["wsl.exe", "bash", "-lc", f"cd {shlex.quote(wsl_cwd)} && {wsl_command}"]
    return command


def _relative_to_project(path: Path) -> str:
    """把项目内路径显示成相对路径，项目外路径保持原样。"""
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def _relative_to_cwd(path: Path, cwd: Path) -> str:
    """把项目内路径显示成相对当前命令工作目录的路径。"""
    try:
        path.resolve().relative_to(PROJECT_ROOT)
    except ValueError:
        return str(path)
    return Path(os.path.relpath(path.resolve(), cwd.resolve())).as_posix()


def _display_arg(arg: object, cwd: Path) -> str:
    """把命令参数转换成 dry-run 使用的相对路径文本。"""
    if isinstance(arg, Path):
        return _relative_to_cwd(arg, cwd)
    raw = str(arg)
    try:
        path = Path(raw)
        if path.is_absolute():
            return _relative_to_cwd(path, cwd)
    except OSError:
        pass
    return raw


def _format_dry_run_command(cwd: Path, args: list[object]) -> str:
    """生成适合 README/调试展示的命令，避免暴露本机绝对路径。"""
    command_text = subprocess.list2cmdline([_display_arg(arg, cwd) for arg in args])
    project_from_cwd = Path(os.path.relpath(PROJECT_ROOT, cwd.resolve())).as_posix()
    replacements = {
        str(PROJECT_ROOT): project_from_cwd,
        str(PROJECT_ROOT).replace("/", "\\"): project_from_cwd,
        _windows_path_to_wsl(str(PROJECT_ROOT)): project_from_cwd,
    }
    for old, new in replacements.items():
        command_text = command_text.replace(old, new)

    cwd_text = _relative_to_project(cwd)
    if cwd_text == ".":
        return command_text
    return f"cd {cwd_text} && {command_text}"


def _run(cwd: Path, args: list[object], *, dry_run: bool = False) -> int:
    """执行命令；dry-run 模式只打印最终命令，不真正启动训练或仿真。"""
    command = _build_process_command(cwd, args)
    if dry_run:
        print(_format_dry_run_command(cwd, args))
        return 0
    completed = subprocess.run(command, cwd=cwd if command[0] != "wsl.exe" else None)
    return completed.returncode


def _latest_checkpoint(log_root: Path) -> Path:
    """在训练日志目录中找到最近修改的 model_*.pt checkpoint。"""
    checkpoints = sorted(
        log_root.glob("logs/rsl_rl/**/model_*.pt"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not checkpoints:
        raise FileNotFoundError(f"No model_*.pt checkpoint found under {log_root / 'logs' / 'rsl_rl'}")
    return checkpoints[0]


def _latest_onnx(log_root: Path) -> Path:
    """在训练日志目录中找到最近导出的 policy.onnx。"""
    onnx_files = sorted(
        log_root.glob("logs/rsl_rl/**/policy.onnx"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not onnx_files:
        raise FileNotFoundError(f"No policy.onnx found under {log_root / 'logs' / 'rsl_rl'}")
    return onnx_files[0]


def _add_common_runtime_args(parser: argparse.ArgumentParser) -> None:
    """给训练和回放类命令添加通用参数。"""
    parser.add_argument("--python", default=DEFAULT_MJLAB_PYTHON, help="Python executable for mjlab train/play.")
    parser.add_argument("--dry-run", action="store_true", help="Print the generated command without running it.")


def _build_parser() -> argparse.ArgumentParser:
    """定义所有对外 CLI 子命令和参数。"""
    parser = argparse.ArgumentParser(description="G1 23DoF training, playback, and simulation CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Show the simplified project status.")
    subparsers.add_parser("check-paths", help="Check the main G1 23DoF paths.")

    prepare_motion = subparsers.add_parser("prepare-motion", help="Copy the default motion asset to runtime.")
    prepare_motion.add_argument("--source", type=Path, default=DEFAULT_SOURCE_MOTION)
    prepare_motion.add_argument("--output", type=Path, default=DEFAULT_RUNTIME_MOTION)
    prepare_motion.add_argument("--dry-run", action="store_true")

    pkl_to_csv = subparsers.add_parser("pkl-to-csv", help="Convert G1 retarget pkl to mjlab CSV.")
    pkl_to_csv.add_argument("input", type=Path)
    pkl_to_csv.add_argument("--output", type=Path, default=DEFAULT_RUNTIME_CSV)
    pkl_to_csv.add_argument("--motion-key")
    pkl_to_csv.add_argument("--robot", choices=["g1_23dof", "g1"], default="g1_23dof")
    pkl_to_csv.add_argument("--dry-run", action="store_true")

    csv_to_npz = subparsers.add_parser("csv-to-npz", help="Convert mjlab CSV to tracking npz.")
    _add_common_runtime_args(csv_to_npz)
    csv_to_npz.add_argument("input", type=Path)
    csv_to_npz.add_argument("--output", type=Path, default=DEFAULT_RUNTIME_MOTION)
    csv_to_npz.add_argument("--robot", choices=["g1_23dof", "g1"], default="g1_23dof")
    csv_to_npz.add_argument("--input-fps", type=float, default=30.0)
    csv_to_npz.add_argument("--output-fps", type=float, default=50.0)
    csv_to_npz.add_argument("--device", default="cuda:0")
    csv_to_npz.add_argument("--render", action="store_true")

    video_to_smpl = subparsers.add_parser("video-to-smpl", help="Convert mp4 video to standard SMPL npz with GVHMR.")
    video_to_smpl.add_argument("video", type=Path)
    video_to_smpl.add_argument("--python", default=DEFAULT_GVHMR_PYTHON)
    video_to_smpl.add_argument("--output", type=Path)
    video_to_smpl.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "runtime" / "video_smpl")
    video_to_smpl.add_argument("--static-cam", action="store_true")
    video_to_smpl.add_argument("--use-dpvo", action="store_true")
    video_to_smpl.add_argument("--f-mm", type=int)
    video_to_smpl.add_argument("--person", type=int, default=0, help="Target person index in multi-person videos.")
    video_to_smpl.add_argument("--fps", type=int, default=30)
    video_to_smpl.add_argument("--frame", choices=["global", "incam"], default="global")
    video_to_smpl.add_argument("--skip-demo", action="store_true", help="Only convert an existing hmr4d_results.pt.")
    video_to_smpl.add_argument("--results", type=Path, help="Existing GVHMR hmr4d_results.pt when using --skip-demo.")
    video_to_smpl.add_argument("--dry-run", action="store_true")

    motion_pipeline_parser = subparsers.add_parser(
        "motion-pipeline",
        help="Run the integrated mp4 -> SMPL -> G1 retarget -> CSV -> NPZ data pipeline.",
    )
    motion_pipeline_parser.add_argument("video", type=Path)
    motion_pipeline_parser.add_argument("--name", help="Runtime case name. Defaults to the input video stem.")
    motion_pipeline_parser.add_argument("--person", type=int, default=0)
    motion_pipeline_parser.add_argument("--runtime-root", type=Path, default=PROJECT_ROOT / "runtime" / "motion_pipeline")
    motion_pipeline_parser.add_argument("--gvhmr-python", default=DEFAULT_GVHMR_PYTHON)
    motion_pipeline_parser.add_argument("--retarget-python", default=DEFAULT_RETARGET_PYTHON)
    motion_pipeline_parser.add_argument("--mjlab-python", default=DEFAULT_MJLAB_PYTHON)
    motion_pipeline_parser.add_argument("--robot", choices=["g1_23dof", "g1"], default="g1_23dof")
    motion_pipeline_parser.add_argument("--input-fps", type=float, default=30.0)
    motion_pipeline_parser.add_argument("--output-fps", type=float, default=50.0)
    motion_pipeline_parser.add_argument("--device", default="cuda:0")
    motion_pipeline_parser.add_argument("--skip-video-demo", action="store_true")
    motion_pipeline_parser.add_argument("--skip-retarget", action="store_true")
    motion_pipeline_parser.add_argument("--retarget-pkl", type=Path, help="Use an existing retarget pkl instead of the default pipeline output.")
    motion_pipeline_parser.add_argument("--motion-key")
    motion_pipeline_parser.add_argument("--dry-run", action="store_true")

    retarget_mink = subparsers.add_parser(
        "retarget-motion",
        help="Run SMPL-to-G1 motion retargeting with the default Mink backend.",
    )
    retarget_mink.add_argument("motion_folder", type=Path)
    retarget_mink.add_argument("--python", default=DEFAULT_RETARGET_PYTHON)
    retarget_mink.add_argument("--correct", action="store_true")
    retarget_mink.add_argument("--dry-run", action="store_true")
    retarget_mink.add_argument("--extra", nargs="*", default=[], help="Extra args passed to convert_fit_motion.py.")

    retarget_phc = subparsers.add_parser("retarget-motion-phc", help="Run SMPL-to-G1 motion retargeting with the PHC backend.")
    retarget_phc.add_argument("motion_folder", type=Path)
    retarget_phc.add_argument("--python", default=DEFAULT_RETARGET_PYTHON)
    retarget_phc.add_argument("--robot", default="unitree_g1_29dof_anneal_23dof")
    retarget_phc.add_argument("--dry-run", action="store_true")
    retarget_phc.add_argument("--extra", nargs="*", default=[], help="Extra Hydra overrides.")

    filter_smpl = subparsers.add_parser("filter-smpl-motion", help="Run the optional SMPL motion filter.")
    filter_smpl.add_argument("motion_folder", type=Path)
    filter_smpl.add_argument("--python", default=DEFAULT_RETARGET_PYTHON)
    filter_smpl.add_argument("--convert-rot", choices=["True", "False"], default="True")
    filter_smpl.add_argument("--dry-run", action="store_true")
    filter_smpl.add_argument("--extra", nargs="*", default=[], help="Extra args passed to motion_filter.py.")

    install_poselib = subparsers.add_parser("install-retarget-poselib", help="Install bundled retarget poselib into the active Python env.")
    install_poselib.add_argument("--python", default=DEFAULT_RETARGET_PYTHON)
    install_poselib.add_argument("--dry-run", action="store_true")

    train_velocity = subparsers.add_parser("train-velocity", help="Train the G1 23DoF velocity policy.")
    _add_common_runtime_args(train_velocity)
    train_velocity.add_argument("--task", default=DEFAULT_VELOCITY_TASK)
    train_velocity.add_argument("--num-envs", type=int, default=4096)
    train_velocity.add_argument("--max-iterations", type=int, help="Override PPO training iterations.")
    train_velocity.add_argument("--gpu-ids", nargs="*", type=int)
    train_velocity.add_argument("--extra", nargs="*", default=[], help="Extra args passed to scripts/train.py.")

    train_tracking = subparsers.add_parser("train-tracking", help="Train the G1 23DoF motion-tracking policy.")
    _add_common_runtime_args(train_tracking)
    train_tracking.add_argument("--task", default=DEFAULT_TRACKING_TASK)
    train_tracking.add_argument("--motion-file", type=Path, default=DEFAULT_RUNTIME_MOTION)
    train_tracking.add_argument("--num-envs", type=int, default=4096)
    train_tracking.add_argument("--max-iterations", type=int, help="Override PPO training iterations.")
    train_tracking.add_argument("--gpu-ids", nargs="*", type=int)
    train_tracking.add_argument("--extra", nargs="*", default=[], help="Extra args passed to scripts/train.py.")

    play_velocity = subparsers.add_parser("play-velocity", help="Play a trained velocity checkpoint.")
    _add_common_runtime_args(play_velocity)
    play_velocity.add_argument("--task", default=DEFAULT_VELOCITY_TASK)
    play_velocity.add_argument("--checkpoint", type=Path)
    play_velocity.add_argument("--num-envs", type=int, default=1)
    play_velocity.add_argument("--agent", choices=["trained", "zero", "random"], default="trained")

    play_tracking = subparsers.add_parser("play-tracking", help="Play a trained motion-tracking checkpoint.")
    _add_common_runtime_args(play_tracking)
    play_tracking.add_argument("--task", default=DEFAULT_TRACKING_TASK)
    play_tracking.add_argument("--motion-file", type=Path, default=DEFAULT_RUNTIME_MOTION)
    play_tracking.add_argument("--checkpoint", type=Path)
    play_tracking.add_argument("--num-envs", type=int, default=1)
    play_tracking.add_argument("--agent", choices=["trained", "zero", "random"], default="trained")

    play_onnx = subparsers.add_parser("play-onnx", help="Play an exported ONNX policy.")
    _add_common_runtime_args(play_onnx)
    play_onnx.add_argument("--task", default=DEFAULT_VELOCITY_TASK)
    play_onnx.add_argument("--onnx-file", type=Path)
    play_onnx.add_argument("--motion-file", type=Path)
    play_onnx.add_argument("--num-envs", type=int, default=1)

    build_sim = subparsers.add_parser(
        "build-sim",
        aliases=["build-23dof-sim"],
        help="Build MuJoCo simulator and G1 23DoF controller.",
    )
    build_sim.add_argument("--dry-run", action="store_true")

    sim = subparsers.add_parser("sim", aliases=["sim-23dof"], help="Run the MuJoCo simulator.")
    sim.add_argument("--dry-run", action="store_true")

    deploy_sim = subparsers.add_parser(
        "deploy-sim",
        aliases=["deploy-23dof-sim"],
        help="Run the G1 23DoF controller against local simulation.",
    )
    deploy_sim.add_argument("--network", default="lo")
    deploy_sim.add_argument("--dry-run", action="store_true")

    sim_stack = subparsers.add_parser(
        "sim-stack",
        aliases=["sim-23dof-stack"],
        help="Run simulator and local G1 23DoF controller together.",
    )
    sim_stack.add_argument("--network", default="lo")
    sim_stack.add_argument("--startup-delay", type=float, default=2.0)
    sim_stack.add_argument("--dry-run", action="store_true")

    sim_29dof = subparsers.add_parser(
        "sim-29dof-mujoco",
        help="Run the 29DoF trained-policy MuJoCo deployment demo.",
    )
    sim_29dof.add_argument("--python", default=DEFAULT_29DOF_PYTHON)
    sim_29dof.add_argument("--xml-path", help="Hydra override, e.g. g1_description/g1_29dof_LieDown.xml")
    sim_29dof.add_argument("--override", nargs="*", default=[], help="Extra Hydra overrides passed to deploy_mujoco.py.")
    sim_29dof.add_argument("--dry-run", action="store_true")

    deploy_29dof_real = subparsers.add_parser(
        "deploy-29dof-real",
        help="Run the 29DoF real-robot deployment entry. Use only after hardware safety checks.",
    )
    deploy_29dof_real.add_argument("--python", default=DEFAULT_29DOF_PYTHON)
    deploy_29dof_real.add_argument("--dry-run", action="store_true")

    return parser


def _format_exists(path: Path) -> str:
    """把路径存在性格式化成 [yes]/[no]，便于 status/check-paths 输出。"""
    return f"[{'yes' if path.exists() else 'no '}] {_relative_to_project(path)}"


def _handle_status() -> None:
    """打印项目最核心的状态：根目录、训练引擎、默认任务和动作文件。"""
    print("G1 23DoF 项目状态")
    print("=" * 18)
    print("项目根目录: .")
    print(f"训练引擎: {_format_exists(ENGINE_ROOT)}")
    print(f"23DoF 部署层: {_format_exists(DEPLOY_23DOF_ROOT)}")
    print(f"29DoF 部署层: {_format_exists(DEPLOY_29DOF_ROOT)}")
    print(f"速度跟踪任务: {DEFAULT_VELOCITY_TASK}")
    print(f"动作跟踪任务: {DEFAULT_TRACKING_TASK}")
    print(f"默认源动作: {_format_exists(DEFAULT_SOURCE_MOTION)}")
    print(f"运行时动作: {_format_exists(DEFAULT_RUNTIME_MOTION)}")


def _handle_check_paths() -> None:
    """检查主流程必须存在的文件，避免训练前才发现路径缺失。"""
    paths = [
        ENGINE_ROOT / "scripts" / "train.py",
        ENGINE_ROOT / "scripts" / "play.py",
        ENGINE_ROOT / "scripts" / "play_onnx.py",
        DEFAULT_SOURCE_MOTION,
        DEFAULT_RUNTIME_MOTION,
        MOTION_PIPELINE_ROOT / "pipeline.py",
        MOTION_PIPELINE_ROOT / "converters" / "pkl_to_csv.py",
        MOTION_PIPELINE_ROOT / "converters" / "gvhmr_to_smpl.py",
        GVHMR_ROOT / "tools" / "demo" / "demo.py",
        SMPL_RETARGET_ROOT / "mink_retarget" / "convert_fit_motion.py",
        SMPL_RETARGET_ROOT / "phc_retarget" / "fit_smpl_motion.py",
        SMPL_RETARGET_ROOT / "motion_filter" / "utils" / "motion_filter.py",
        MOTION_RETARGET_ROOT / "description" / "robots" / "g1" / "dof_axis.npy",
        ENGINE_ROOT / "scripts" / "csv_to_npz.py",
        DEPLOY_23DOF_ROOT / "CMakeLists.txt",
        ENGINE_ROOT / "simulate" / "CMakeLists.txt",
        DEPLOY_29DOF_ROOT / "deploy_mujoco" / "deploy_mujoco.py",
        DEPLOY_29DOF_ROOT / "deploy_real" / "deploy_real.py",
        DEPLOY_29DOF_ROOT / "policy" / "loco_mode" / "model" / "policy_29dof.pt",
    ]
    for path in paths:
        print(_format_exists(path))


def _handle_prepare_motion(args: argparse.Namespace) -> int:
    """把默认参考动作复制到 runtime 目录，作为动作跟踪训练默认输入。"""
    source = args.source.resolve()
    output = args.output.resolve()
    if args.dry_run:
        print(f"copy {source} -> {output}")
        return 0
    if not source.exists():
        raise FileNotFoundError(f"motion source not found: {source}")
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, output)
    print(f"prepared motion: {output}")
    return 0


def _handle_motion_conversion(args: argparse.Namespace) -> int:
    """处理 G1 retarget pkl -> mjlab CSV -> mjlab NPZ 的动作转换命令。"""
    if args.command == "pkl-to-csv":
        command = motion_pipeline.pkl_to_csv_command(
            input_path=args.input,
            output_path=args.output,
            robot=args.robot,
            motion_key=args.motion_key,
        )
        return _run(PROJECT_ROOT, command, dry_run=args.dry_run)

    if args.command == "csv-to-npz":
        command = motion_pipeline.csv_to_npz_command(
            input_path=args.input,
            output_path=args.output,
            python=args.python,
            robot=args.robot,
            input_fps=args.input_fps,
            output_fps=args.output_fps,
            device=args.device,
            render=args.render,
        )
        return _run(ENGINE_ROOT, command, dry_run=args.dry_run)

    return -1


def _handle_video_smpl(args: argparse.Namespace) -> int:
    """运行 mp4 -> GVHMR -> 标准 SMPL npz 的视频动作前端。"""
    if args.command != "video-to-smpl":
        return -1

    video_path = _resolve_user_path(args.video)
    output_root = _resolve_user_path(args.output_root)
    output_path = _resolve_user_path(args.output) if args.output else output_root / f"{video_path.stem}.npz"
    commands = motion_pipeline.video_to_smpl_commands(
        video=video_path,
        output=output_path,
        output_root=output_root,
        python=args.python,
        person=args.person,
        static_cam=args.static_cam,
        use_dpvo=args.use_dpvo,
        f_mm=args.f_mm,
        fps=args.fps,
        frame=args.frame,
        skip_demo=args.skip_demo,
        results=args.results,
    )

    if args.dry_run:
        for command in commands:
            print(_format_dry_run_command(GVHMR_ROOT, command))
        return 0

    for command in commands:
        result = _run(GVHMR_ROOT, command)
        if result != 0:
            return result
    return 0


def _handle_motion_retarget(args: argparse.Namespace) -> int:
    """运行本项目接入的 SMPL 到 G1 动作重定向工具链。"""
    if args.command == "retarget-motion":
        command = motion_pipeline.retarget_motion_command(
            motion_folder=args.motion_folder,
            python=args.python,
            correct=args.correct,
            extra=args.extra,
        )
        return _run(SMPL_RETARGET_ROOT, command, dry_run=args.dry_run)

    if args.command == "retarget-motion-phc":
        command = motion_pipeline.retarget_motion_phc_command(
            motion_folder=args.motion_folder,
            python=args.python,
            robot=args.robot,
            extra=args.extra,
        )
        return _run(SMPL_RETARGET_ROOT, command, dry_run=args.dry_run)

    if args.command == "filter-smpl-motion":
        command = motion_pipeline.filter_smpl_motion_command(
            motion_folder=args.motion_folder,
            python=args.python,
            convert_rot=args.convert_rot,
            extra=args.extra,
        )
        return _run(SMPL_RETARGET_ROOT, command, dry_run=args.dry_run)

    if args.command == "install-retarget-poselib":
        poselib_root = SMPL_RETARGET_ROOT / "poselib"
        shell = f"{_quote_shell_arg(args.python)} -m pip install -e {_quote_shell_arg(poselib_root)}"
        return _run(SMPL_RETARGET_ROOT, ["/bin/bash", "-lc", shell], dry_run=args.dry_run)

    return -1


def _handle_motion_pipeline(args: argparse.Namespace) -> int:
    """运行项目级动作数据流水线。

    这是一条给日常使用准备的总入口：输入 mp4，按固定目录产出 SMPL、retarget pkl、
    CSV 和最终 mimic 训练 npz。真实长任务逐步执行；dry-run 会完整打印每一步命令。
    """
    if args.command != "motion-pipeline":
        return -1

    video_path = _resolve_user_path(args.video)
    case_name = args.name or video_path.stem
    case_root = _resolve_user_path(args.runtime_root) / case_name
    smpl_npz = case_root / "source_motion" / f"{case_name}.npz"
    csv_path = case_root / f"{case_name}_g1.csv"
    npz_path = case_root / f"{case_name}_g1.npz"
    retarget_pkl = (
        _resolve_user_path(args.retarget_pkl)
        if args.retarget_pkl
        else SMPL_RETARGET_ROOT / "retargeted_motion_data" / "mink" / f"{case_name}.pkl"
    )

    commands: list[tuple[Path, list[object]]] = []
    for command in motion_pipeline.video_to_smpl_commands(
        video=video_path,
        output=smpl_npz,
        output_root=case_root / "video_smpl",
        python=args.gvhmr_python,
        person=args.person,
        skip_demo=args.skip_video_demo,
    ):
        commands.append((GVHMR_ROOT, command))

    if not args.skip_retarget:
        commands.append(
            (
                SMPL_RETARGET_ROOT,
                motion_pipeline.retarget_motion_command(
                    motion_folder=case_root,
                    python=args.retarget_python,
                ),
            )
        )

    commands.append(
        (
            PROJECT_ROOT,
            motion_pipeline.pkl_to_csv_command(
                input_path=retarget_pkl,
                output_path=csv_path,
                robot=args.robot,
                motion_key=args.motion_key,
            ),
        )
    )
    commands.append(
        (
            ENGINE_ROOT,
            motion_pipeline.csv_to_npz_command(
                input_path=csv_path,
                output_path=npz_path,
                python=args.mjlab_python,
                robot=args.robot,
                input_fps=args.input_fps,
                output_fps=args.output_fps,
                device=args.device,
            ),
        )
    )

    if args.dry_run:
        print(f"case_root={_relative_to_project(case_root)}")
        print(f"final_motion={_relative_to_project(npz_path)}")
        for cwd, command in commands:
            print(_format_dry_run_command(cwd, command))
        return 0

    case_root.mkdir(parents=True, exist_ok=True)
    for cwd, command in commands:
        result = _run(cwd, command)
        if result != 0:
            return result
    print(f"motion npz ready: {npz_path}")
    return 0


def _train_command(args: argparse.Namespace, *, tracking: bool) -> list[object]:
    """生成底层 scripts/train.py 训练命令。

    tracking=False 对应速度跟踪；tracking=True 对应动作跟踪，并额外传入
    --motion-file。
    """
    command: list[object] = [args.python, ENGINE_ROOT / "scripts" / "train.py", args.task]
    if tracking:
        command.extend(["--motion-file", _resolve_user_path(args.motion_file)])
    command.append(f"--env.scene.num-envs={args.num_envs}")
    if args.max_iterations is not None:
        command.append(f"--agent.max-iterations={args.max_iterations}")
    if args.gpu_ids:
        command.append("--gpu-ids")
        command.extend(args.gpu_ids)
    command.extend(args.extra)
    return command


def _play_command(args: argparse.Namespace, *, tracking: bool) -> list[object]:
    """生成底层 scripts/play.py 回放命令。"""
    command: list[object] = [
        args.python,
        ENGINE_ROOT / "scripts" / "play.py",
        args.task,
        f"--agent={args.agent}",
        f"--num-envs={args.num_envs}",
    ]
    if tracking:
        command.extend(["--motion-file", _resolve_user_path(args.motion_file)])
    if args.agent == "trained":
        checkpoint = args.checkpoint or _latest_checkpoint(ENGINE_ROOT)
        command.extend(["--checkpoint-file", checkpoint])
    return command


def _handle_training_or_play(args: argparse.Namespace) -> int:
    """分发训练和策略回放命令，返回子进程退出码。"""
    if args.command == "train-velocity":
        return _run(ENGINE_ROOT, _train_command(args, tracking=False), dry_run=args.dry_run)
    if args.command == "train-tracking":
        return _run(ENGINE_ROOT, _train_command(args, tracking=True), dry_run=args.dry_run)
    if args.command == "play-velocity":
        return _run(ENGINE_ROOT, _play_command(args, tracking=False), dry_run=args.dry_run)
    if args.command == "play-tracking":
        return _run(ENGINE_ROOT, _play_command(args, tracking=True), dry_run=args.dry_run)
    if args.command == "play-onnx":
        onnx_file = args.onnx_file or _latest_onnx(ENGINE_ROOT)
        command: list[object] = [
            args.python,
            ENGINE_ROOT / "scripts" / "play_onnx.py",
            args.task,
            "--onnx-file",
            onnx_file,
            f"--num-envs={args.num_envs}",
        ]
        if args.motion_file:
            command.extend(["--motion-file", _resolve_user_path(args.motion_file)])
        return _run(ENGINE_ROOT, command, dry_run=args.dry_run)
    return -1


def _handle_sim(args: argparse.Namespace) -> int:
    """分发部署侧仿真命令。

    build-sim 负责编译 MuJoCo 仿真器和 G1 控制器；sim-stack 会先启动
    unitree_mujoco，再启动 g1_ctrl，适合本地闭环仿真。
    """
    if args.command in {"build-sim", "build-23dof-sim"}:
        command = [
            "/bin/bash",
            "-lc",
            "cmake -S simulate -B simulate/build && "
            "cmake --build simulate/build -j8 && "
            "cmake -S deploy/robots/g1_23dof -B deploy/robots/g1_23dof/build && "
            "cmake --build deploy/robots/g1_23dof/build -j8",
        ]
        return _run(ENGINE_ROOT, command, dry_run=args.dry_run)
    if args.command in {"sim", "sim-23dof"}:
        return _run(ENGINE_ROOT, ["/bin/bash", "-lc", "./simulate/build/unitree_mujoco"], dry_run=args.dry_run)
    if args.command in {"deploy-sim", "deploy-23dof-sim"}:
        return _run(
            ENGINE_ROOT,
            ["/bin/bash", "-lc", f"./deploy/robots/g1_23dof/build/g1_ctrl --network={shlex.quote(args.network)}"],
            dry_run=args.dry_run,
        )
    if args.command in {"sim-stack", "sim-23dof-stack"}:
        sim_cmd = _build_process_command(ENGINE_ROOT, ["/bin/bash", "-lc", "./simulate/build/unitree_mujoco"])
        ctrl_cmd = _build_process_command(
            ENGINE_ROOT,
            ["/bin/bash", "-lc", f"./deploy/robots/g1_23dof/build/g1_ctrl --network={shlex.quote(args.network)}"],
        )
        if args.dry_run:
            print(_format_dry_run_command(ENGINE_ROOT, ["/bin/bash", "-lc", "./simulate/build/unitree_mujoco"]))
            print(_format_dry_run_command(ENGINE_ROOT, ["/bin/bash", "-lc", f"./deploy/robots/g1_23dof/build/g1_ctrl --network={shlex.quote(args.network)}"]))
            return 0
        sim_proc = subprocess.Popen(sim_cmd)
        try:
            import time

            time.sleep(args.startup_delay)
            ctrl_proc = subprocess.Popen(ctrl_cmd)
            return ctrl_proc.wait()
        finally:
            if sim_proc.poll() is None:
                sim_proc.terminate()
    return -1


def _handle_29dof_deploy(args: argparse.Namespace) -> int:
    """运行 29DoF 已训练策略部署层。

    这层不参与 23DoF 训练闭环，主要用于已有 29DoF 策略的 MuJoCo 演示和真机部署复现。
    """
    if args.command == "sim-29dof-mujoco":
        command: list[object] = [args.python, DEPLOY_29DOF_ROOT / "deploy_mujoco" / "deploy_mujoco.py"]
        if args.xml_path:
            command.append(f"xml_path={args.xml_path}")
        command.extend(args.override)
        return _run(DEPLOY_29DOF_ROOT, command, dry_run=args.dry_run)
    if args.command == "deploy-29dof-real":
        return _run(
            DEPLOY_29DOF_ROOT,
            [args.python, DEPLOY_29DOF_ROOT / "deploy_real" / "deploy_real.py"],
            dry_run=args.dry_run,
        )
    return -1


def main() -> None:
    """CLI 主函数：解析参数，并按命令类型调用对应处理函数。"""
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "status":
        _handle_status()
        return
    if args.command == "check-paths":
        _handle_check_paths()
        return
    if args.command == "prepare-motion":
        raise SystemExit(_handle_prepare_motion(args))

    conversion_result = _handle_motion_conversion(args)
    if conversion_result >= 0:
        raise SystemExit(conversion_result)

    video_smpl_result = _handle_video_smpl(args)
    if video_smpl_result >= 0:
        raise SystemExit(video_smpl_result)

    motion_pipeline_result = _handle_motion_pipeline(args)
    if motion_pipeline_result >= 0:
        raise SystemExit(motion_pipeline_result)

    retarget_result = _handle_motion_retarget(args)
    if retarget_result >= 0:
        raise SystemExit(retarget_result)

    runtime_result = _handle_training_or_play(args)
    if runtime_result >= 0:
        raise SystemExit(runtime_result)

    sim_result = _handle_sim(args)
    if sim_result >= 0:
        raise SystemExit(sim_result)

    deploy_29dof_result = _handle_29dof_deploy(args)
    if deploy_29dof_result >= 0:
        raise SystemExit(deploy_29dof_result)

    parser.error(f"unknown command: {args.command}")


if __name__ == "__main__":
    main()
