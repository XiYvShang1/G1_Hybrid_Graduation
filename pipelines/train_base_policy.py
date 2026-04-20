"""Register or launch base locomotion training through project-local entrypoints."""

from __future__ import annotations

import argparse
from pathlib import Path

from adapters.base import BasePolicyAdapter
from registry_manager import load_yaml_config, upsert_registry_item


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="基础运动策略训练入口")
    parser.add_argument("--task-id", default="Unitree-G1-23Dof-Flat")
    parser.add_argument("--num-envs", type=int, default=128)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    project_root = Path(__file__).resolve().parents[1]
    adapter = BasePolicyAdapter(project_root)
    plan = adapter.build_base_policy_plan(
        upstream_task_id=args.task_id,
        num_envs=args.num_envs,
    )
    config_path = project_root / "configs" / "tasks" / "example_base_velocity_task.yaml"
    payload = load_yaml_config(config_path)
    registry_path = upsert_registry_item(project_root, "tasks", payload)
    print("Base policy pipeline")
    for key, value in plan.items():
        print(f"{key}: {value}")
    print(f"registered_to: {registry_path}")


if __name__ == "__main__":
    main()
