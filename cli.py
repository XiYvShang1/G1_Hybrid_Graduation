"""Unified CLI entrypoint for the G1 hybrid project."""

from __future__ import annotations

import argparse
from pathlib import Path

from registry_manager import (
    build_closure_report,
    collect_path_checks,
    format_path_checks,
    format_registry_status,
    load_yaml_config,
    load_registry_bundle,
    reset_registry_to_examples,
    upsert_registry_item,
)
from workflow_runner import WorkflowRunner


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="G1 混合动作策略项目统一入口")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status", help="显示当前 registry 状态")
    status_parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="项目根目录，默认自动定位为当前包目录",
    )

    check_parser = subparsers.add_parser(
        "check-paths", help="检查 registry 中路径是否存在"
    )
    check_parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="项目根目录，默认自动定位为当前包目录",
    )

    closure_parser = subparsers.add_parser("show-closure", help="显示当前最小闭环报告")
    closure_parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="项目根目录，默认自动定位为当前包目录",
    )

    add_motion_parser = subparsers.add_parser(
        "add-motion", help="从 YAML 配置注册动作资产"
    )
    add_motion_parser.add_argument(
        "--config", type=Path, required=True, help="动作资产配置 YAML 路径"
    )
    add_motion_parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="项目根目录，默认自动定位为当前包目录",
    )

    add_task_parser = subparsers.add_parser("add-task", help="从 YAML 配置注册训练任务")
    add_task_parser.add_argument(
        "--config", type=Path, required=True, help="训练任务配置 YAML 路径"
    )
    add_task_parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="项目根目录，默认自动定位为当前包目录",
    )

    add_policy_parser = subparsers.add_parser(
        "add-policy", help="从 YAML 配置注册策略产物"
    )
    add_policy_parser.add_argument(
        "--config", type=Path, required=True, help="策略配置 YAML 路径"
    )
    add_policy_parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="项目根目录，默认自动定位为当前包目录",
    )

    reset_parser = subparsers.add_parser(
        "reset-example-registry", help="重置 registry 为示例配置"
    )
    reset_parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="项目根目录，默认自动定位为当前包目录",
    )

    workflow_parser = subparsers.add_parser(
        "workflow", help="串联 motion/base/skill 三段命令"
    )
    workflow_parser.add_argument(
        "--config", type=Path, required=True, help="workflow YAML 配置路径"
    )
    workflow_parser.add_argument(
        "--execute", action="store_true", help="实际执行配置中允许执行的阶段"
    )
    workflow_parser.add_argument(
        "--stages",
        nargs="*",
        default=["motion", "base", "skill"],
        choices=["motion", "base", "skill"],
        help="要包含的阶段，默认全部",
    )
    workflow_parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="项目根目录，默认自动定位为当前包目录",
    )

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

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
        print(f"已注册动作资产到: {registry_path}")
        print(f"asset_id: {payload.get('asset_id', 'unknown')}")
        return

    if args.command == "add-task":
        payload = load_yaml_config(args.config)
        registry_path = upsert_registry_item(args.project_root, "tasks", payload)
        print(f"已注册训练任务到: {registry_path}")
        print(f"task_id: {payload.get('task_id', 'unknown')}")
        return

    if args.command == "add-policy":
        payload = load_yaml_config(args.config)
        registry_path = upsert_registry_item(args.project_root, "policies", payload)
        print(f"已注册策略产物到: {registry_path}")
        print(f"policy_id: {payload.get('policy_id', 'unknown')}")
        return

    if args.command == "reset-example-registry":
        updated_files = reset_registry_to_examples(args.project_root)
        print("已重置 registry 示例配置:")
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

    parser.error(f"未知命令: {args.command}")


if __name__ == "__main__":
    main()
