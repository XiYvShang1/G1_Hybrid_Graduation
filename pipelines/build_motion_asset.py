"""Build or register a motion asset for the G1 hybrid project."""

from __future__ import annotations

from pathlib import Path

from adapters.motion import MotionAssetAdapter
from path_utils import resolve_workspace_path
from registry_manager import load_yaml_config, upsert_registry_item


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    config_path = project_root / "configs" / "assets" / "example_motion_asset.yaml"
    payload = load_yaml_config(config_path)
    adapter = MotionAssetAdapter(project_root)
    plan = adapter.build_motion_asset_plan(
        source_path=resolve_workspace_path(project_root, payload["source_path"]),
        target_path=resolve_workspace_path(project_root, payload["artifact_path"]),
    )
    registry_path = upsert_registry_item(project_root, "motions", payload)
    print("Motion asset pipeline")
    for key, value in plan.items():
        print(f"{key}: {value}")
    print(f"registered_to: {registry_path}")


if __name__ == "__main__":
    main()
