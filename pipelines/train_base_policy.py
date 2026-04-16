"""Register or launch base locomotion training through unitree_rl_mjlab."""

from __future__ import annotations

from pathlib import Path

from adapters.mjlab import MJLabAdapter
from path_utils import detect_workspace_root
from registry_manager import (
    load_yaml_config,
    upsert_registry_item,
)


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    workspace_root = detect_workspace_root(project_root)
    adapter = MJLabAdapter(workspace_root / "unitree_rl_mjlab")
    plan = adapter.build_base_policy_plan(upstream_task_id="Unitree-G1-23Dof-Flat")
    config_path = project_root / "configs" / "tasks" / "example_base_velocity_task.yaml"
    payload = load_yaml_config(config_path)
    registry_path = upsert_registry_item(project_root, "tasks", payload)
    print("Base policy pipeline stage-2 skeleton")
    for key, value in plan.items():
        print(f"{key}: {value}")
    print(f"registered_to: {registry_path}")


if __name__ == "__main__":
    main()
