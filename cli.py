"""Unified CLI entrypoint for the G1 23DoF project."""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path, PureWindowsPath

from registry_manager import (
    build_closure_report,
    collect_path_checks,
    format_path_checks,
    format_registry_status,
    load_registry_bundle,
    load_yaml_config,
    reset_registry_to_examples,
    upsert_registry_item,
)
from workflow_runner import WorkflowRunner


PROJECT_ROOT = Path(__file__).resolve().parent
ENGINE_ROOT = PROJECT_ROOT / "engines" / "base_locomotion"
DEFAULT_WSL_PYTHON = "/home/xiyv/miniconda3/envs/unitree_rl_mjlab/bin/python"
DEFAULT_VELOCITY_TASK = "Unitree-G1-23Dof-Flat"
DEFAULT_TRACKING_TASK = "Unitree-G1-23Dof-Tracking"
DEFAULT_MOTION_FILE = PROJECT_ROOT / "runtime" / "example_motion" / "example_motion.npz"


def _windows_path_to_wsl(raw_path: str) -> str:
    path = PureWindowsPath(raw_path)
    if not path.drive:
        return raw_path
    drive = path.drive.rstrip(":").lower()
    parts = [part for part in path.parts[1:] if part not in {"\\", "/"}]
    return "/mnt/" + drive + "/" + "/".join(parts)


def _arg_for_shell(arg: object) -> str:
    raw = str(arg)
    if os.name == "nt" and PureWindowsPath(raw).drive:
        return _windows_path_to_wsl(raw)
    return raw


def _build_process_command(cwd: Path, args: list[object]) -> list[str]:
    command = [str(arg) for arg in args]
    if os.name == "nt" and command and command[0].startswith("/"):
        wsl_cwd = _windows_path_to_wsl(str(cwd))
        wsl_command = " ".join(shlex.quote(_arg_for_shell(arg)) for arg in command)
        return ["wsl.exe", "bash", "-lc", f"cd {shlex.quote(wsl_cwd)} && {wsl_command}"]
    return command


def _run(cwd: Path, args: list[object], *, dry_run: bool = False) -> int:
    command = _build_process_command(cwd, args)
    printable = subprocess.list2cmdline(command)
    if dry_run:
        print(printable)
        return 0
    completed = subprocess.run(command, cwd=cwd if command[0] != "wsl.exe" else None)
    return completed.returncode


def _latest_checkpoint(log_root: Path) -> Path:
    checkpoints = sorted(
        log_root.glob("logs/rsl_rl/**/model_*.pt"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not checkpoints:
        raise FileNotFoundError(f"No model_*.pt checkpoint found under {log_root / 'logs' / 'rsl_rl'}")
    return checkpoints[0]


def _latest_onnx(log_root: Path) -> Path:
    onnx_files = sorted(
        log_root.glob("logs/rsl_rl/**/policy.onnx"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not onnx_files:
        raise FileNotFoundError(f"No policy.onnx found under {log_root / 'logs' / 'rsl_rl'}")
    return onnx_files[0]


def _add_common_runtime_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--python", default=DEFAULT_WSL_PYTHON, help="Python executable for mjlab training/play.")
    parser.add_argument("--dry-run", action="store_true", help="Print the command without executing it.")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="G1 23DoF training, simulation, and registry CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status", help="Show registry status.")
    status_parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)

    check_parser = subparsers.add_parser("check-paths", help="Check registered local paths.")
    check_parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)

    closure_parser = subparsers.add_parser("show-closure", help="Show the current project closure report.")
    closure_parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)

    add_motion_parser = subparsers.add_parser("add-motion", help="Register a motion asset YAML.")
    add_motion_parser.add_argument("--config", type=Path, required=True)
    add_motion_parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)

    add_task_parser = subparsers.add_parser("add-task", help="Register a training task YAML.")
    add_task_parser.add_argument("--config", type=Path, required=True)
    add_task_parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)

    add_policy_parser = subparsers.add_parser("add-policy", help="Register a policy artifact YAML.")
    add_policy_parser.add_argument("--config", type=Path, required=True)
    add_policy_parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)

    reset_parser = subparsers.add_parser("reset-example-registry", help="Reset registry to example entries.")
    reset_parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)

    workflow_parser = subparsers.add_parser("workflow", help="Run the motion/base/skill workflow.")
    workflow_parser.add_argument("--config", type=Path, required=True)
    workflow_parser.add_argument("--execute", action="store_true")
    workflow_parser.add_argument(
        "--stages",
        nargs="*",
        default=["motion", "base", "skill"],
        choices=["motion", "base", "skill"],
    )
    workflow_parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)

    train_velocity = subparsers.add_parser("train-velocity", help="Train the G1 23DoF velocity policy.")
    _add_common_runtime_args(train_velocity)
    train_velocity.add_argument("--task", default=DEFAULT_VELOCITY_TASK)
    train_velocity.add_argument("--num-envs", type=int, default=4096)
    train_velocity.add_argument("--gpu-ids", nargs="*", type=int)

    train_tracking = subparsers.add_parser("train-tracking", help="Train the G1 23DoF motion-tracking policy.")
    _add_common_runtime_args(train_tracking)
    train_tracking.add_argument("--task", default=DEFAULT_TRACKING_TASK)
    train_tracking.add_argument("--motion-file", type=Path, default=DEFAULT_MOTION_FILE)
    train_tracking.add_argument("--num-envs", type=int, default=4096)
    train_tracking.add_argument("--gpu-ids", nargs="*", type=int)

    play_velocity = subparsers.add_parser("play-velocity", help="Play a trained velocity checkpoint.")
    _add_common_runtime_args(play_velocity)
    play_velocity.add_argument("--task", default=DEFAULT_VELOCITY_TASK)
    play_velocity.add_argument("--checkpoint", type=Path)
    play_velocity.add_argument("--num-envs", type=int, default=1)
    play_velocity.add_argument("--agent", choices=["trained", "zero", "random"], default="trained")

    play_tracking = subparsers.add_parser("play-tracking", help="Play a trained motion-tracking checkpoint.")
    _add_common_runtime_args(play_tracking)
    play_tracking.add_argument("--task", default=DEFAULT_TRACKING_TASK)
    play_tracking.add_argument("--motion-file", type=Path, default=DEFAULT_MOTION_FILE)
    play_tracking.add_argument("--checkpoint", type=Path)
    play_tracking.add_argument("--num-envs", type=int, default=1)
    play_tracking.add_argument("--agent", choices=["trained", "zero", "random"], default="trained")

    play_onnx = subparsers.add_parser("play-onnx", help="Play an exported ONNX policy.")
    _add_common_runtime_args(play_onnx)
    play_onnx.add_argument("--task", default=DEFAULT_VELOCITY_TASK)
    play_onnx.add_argument("--onnx-file", type=Path)
    play_onnx.add_argument("--motion-file", type=Path)
    play_onnx.add_argument("--num-envs", type=int, default=1)

    build_sim = subparsers.add_parser("build-sim", help="Build MuJoCo simulator and G1 23DoF controller.")
    build_sim.add_argument("--dry-run", action="store_true")

    sim = subparsers.add_parser("sim", help="Run the MuJoCo simulator.")
    sim.add_argument("--dry-run", action="store_true")

    deploy_sim = subparsers.add_parser("deploy-sim", help="Run the G1 23DoF controller against local simulation.")
    deploy_sim.add_argument("--network", default="lo")
    deploy_sim.add_argument("--dry-run", action="store_true")

    sim_stack = subparsers.add_parser("sim-stack", help="Run simulator and local G1 23DoF controller together.")
    sim_stack.add_argument("--network", default="lo")
    sim_stack.add_argument("--startup-delay", type=float, default=2.0)
    sim_stack.add_argument("--dry-run", action="store_true")

    return parser


def _train_command(args: argparse.Namespace, *, tracking: bool) -> list[object]:
    command: list[object] = [args.python, ENGINE_ROOT / "scripts" / "train.py", args.task]
    if tracking:
        command.extend(["--motion-file", args.motion_file])
    command.append(f"--env.scene.num-envs={args.num_envs}")
    if args.gpu_ids:
        command.append("--gpu-ids")
        command.extend(args.gpu_ids)
    return command


def _play_command(args: argparse.Namespace, *, tracking: bool) -> list[object]:
    command: list[object] = [
        args.python,
        ENGINE_ROOT / "scripts" / "play.py",
        args.task,
        f"--agent={args.agent}",
        f"--num-envs={args.num_envs}",
    ]
    if tracking:
        command.extend(["--motion-file", args.motion_file])
    if args.agent == "trained":
        checkpoint = args.checkpoint or _latest_checkpoint(ENGINE_ROOT)
        command.extend(["--checkpoint-file", checkpoint])
    return command


def _handle_training_or_play(args: argparse.Namespace) -> int:
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
            command.extend(["--motion-file", args.motion_file])
        return _run(ENGINE_ROOT, command, dry_run=args.dry_run)
    return -1


def _handle_sim(args: argparse.Namespace) -> int:
    if args.command == "build-sim":
        command = [
            "/bin/bash",
            "-lc",
            "cmake -S simulate -B simulate/build && "
            "cmake --build simulate/build -j8 && "
            "cmake -S deploy/robots/g1_23dof -B deploy/robots/g1_23dof/build && "
            "cmake --build deploy/robots/g1_23dof/build -j8",
        ]
        return _run(ENGINE_ROOT, command, dry_run=args.dry_run)
    if args.command == "sim":
        return _run(ENGINE_ROOT, ["/bin/bash", "-lc", "./simulate/build/unitree_mujoco"], dry_run=args.dry_run)
    if args.command == "deploy-sim":
        return _run(
            ENGINE_ROOT,
            ["/bin/bash", "-lc", f"./deploy/robots/g1_23dof/build/g1_ctrl --network={shlex.quote(args.network)}"],
            dry_run=args.dry_run,
        )
    if args.command == "sim-stack":
        sim_cmd = _build_process_command(
            ENGINE_ROOT, ["/bin/bash", "-lc", "./simulate/build/unitree_mujoco"]
        )
        ctrl_cmd = _build_process_command(
            ENGINE_ROOT,
            ["/bin/bash", "-lc", f"./deploy/robots/g1_23dof/build/g1_ctrl --network={shlex.quote(args.network)}"],
        )
        if args.dry_run:
            print(subprocess.list2cmdline(sim_cmd))
            print(subprocess.list2cmdline(ctrl_cmd))
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


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    runtime_result = _handle_training_or_play(args)
    if runtime_result >= 0:
        raise SystemExit(runtime_result)

    sim_result = _handle_sim(args)
    if sim_result >= 0:
        raise SystemExit(sim_result)

    if args.command == "status":
        bundle = load_registry_bundle(args.project_root)
        print(format_registry_status(bundle))
        return

    if args.command == "check-paths":
        bundle = load_registry_bundle(args.project_root)
        checks = collect_path_checks(args.project_root, bundle)
        print(format_path_checks(checks))
        return

    if args.command == "show-closure":
        bundle = load_registry_bundle(args.project_root)
        print(build_closure_report(bundle))
        return

    if args.command == "add-motion":
        payload = load_yaml_config(args.config)
        registry_path = upsert_registry_item(args.project_root, "motions", payload)
        print(f"registered motion asset to: {registry_path}")
        print(f"asset_id: {payload.get('asset_id', 'unknown')}")
        return

    if args.command == "add-task":
        payload = load_yaml_config(args.config)
        registry_path = upsert_registry_item(args.project_root, "tasks", payload)
        print(f"registered training task to: {registry_path}")
        print(f"task_id: {payload.get('task_id', 'unknown')}")
        return

    if args.command == "add-policy":
        payload = load_yaml_config(args.config)
        registry_path = upsert_registry_item(args.project_root, "policies", payload)
        print(f"registered policy artifact to: {registry_path}")
        print(f"policy_id: {payload.get('policy_id', 'unknown')}")
        return

    if args.command == "reset-example-registry":
        updated_files = reset_registry_to_examples(args.project_root)
        print("reset registry example configs:")
        for file_path in updated_files:
            print(f"- {file_path}")
        return

    if args.command == "workflow":
        runner = WorkflowRunner(args.project_root)
        workflow_cfg = runner.load_workflow(args.config)
        results = runner.run(
            workflow_cfg=workflow_cfg,
            execute=bool(args.execute),
            selected_stages=set(args.stages),
        )
        print(runner.format_results(results))
        return

    parser.error(f"unknown command: {args.command}")


if __name__ == "__main__":
    main()
