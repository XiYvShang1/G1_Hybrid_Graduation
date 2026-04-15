"""Build or register a motion asset for the hybrid graduation project."""

from __future__ import annotations

from pathlib import Path

from G1_Hybrid_Graduation_Project.adapters.gvhmr2pbhc import GVHMR2PBHCAdapter
from G1_Hybrid_Graduation_Project.registry_manager import (
    load_yaml_config,
    upsert_registry_item,
)


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    workspace_root = project_root.parent
    adapter = GVHMR2PBHCAdapter(workspace_root / "GVHMR2PBHC")
    plan = adapter.build_motion_asset_plan(
        source_path=workspace_root / "GVHMR2PBHC" / "outputs" / "example.npz",
        target_path=workspace_root / "PBHC" / "outputs" / "example_motion.pkl",
    )
    config_path = project_root / "configs" / "assets" / "example_motion_asset.yaml"
    payload = load_yaml_config(config_path)
    registry_path = upsert_registry_item(project_root, "motions", payload)
    print("Motion asset pipeline stage-2 skeleton")
    for key, value in plan.items():
        print(f"{key}: {value}")
    print(f"registered_to: {registry_path}")


if __name__ == "__main__":
    main()
