"""Register or launch skill motion tracking training through PBHC."""

from __future__ import annotations

from pathlib import Path

from adapters.pbhc import PBHCAdapter
from path_utils import detect_workspace_root
from registry_manager import (
    load_yaml_config,
    upsert_registry_item,
)


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    workspace_root = detect_workspace_root(project_root)
    adapter = PBHCAdapter(workspace_root / "PBHC")
    plan = adapter.build_skill_policy_plan(
        motion_asset_id="example_pbhc_motion",
        task_name="g1_skill_motion_tracking",
    )
    config_path = (
        project_root / "configs" / "tasks" / "example_skill_tracking_task.yaml"
    )
    payload = load_yaml_config(config_path)
    registry_path = upsert_registry_item(project_root, "tasks", payload)
    print("Skill policy pipeline stage-2 skeleton")
    for key, value in plan.items():
        print(f"{key}: {value}")
    print(f"registered_to: {registry_path}")


if __name__ == "__main__":
    main()
