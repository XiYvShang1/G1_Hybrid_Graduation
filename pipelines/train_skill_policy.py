"""Register or launch skill motion tracking training through project-local entrypoints."""

from __future__ import annotations

import argparse
from pathlib import Path

from adapters.skill import SkillPolicyAdapter
from registry_manager import load_yaml_config, upsert_registry_item


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="技能动作策略训练入口")
    parser.add_argument("--motion-asset-id", default="example_motion_asset")
    parser.add_argument("--motion-file", default="runtime/example_motion/example_motion.npz")
    parser.add_argument("--task-name", default="Unitree-G1-23Dof-Tracking")
    parser.add_argument("--num-envs", type=int, default=128)
    parser.add_argument("--experiment-name", default="hybrid_debug")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    project_root = Path(__file__).resolve().parents[1]
    adapter = SkillPolicyAdapter(project_root)
    plan = adapter.build_skill_policy_plan(
        motion_asset_id=args.motion_asset_id,
        task_name=args.task_name,
        motion_file=args.motion_file,
        num_envs=args.num_envs,
        experiment_name=args.experiment_name,
    )
    config_path = project_root / "configs" / "tasks" / "example_skill_tracking_task.yaml"
    payload = load_yaml_config(config_path)
    registry_path = upsert_registry_item(project_root, "tasks", payload)
    print("Skill policy pipeline")
    for key, value in plan.items():
        print(f"{key}: {value}")
    print(f"registered_to: {registry_path}")


if __name__ == "__main__":
    main()
