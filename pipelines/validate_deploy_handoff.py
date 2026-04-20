"""Validate whether a registered policy has enough deployment metadata."""

from __future__ import annotations

import argparse


REQUIRED_HANDOFF_FIELDS = [
    "obs_layout_source",
    "action_scale_source",
    "default_pose_source",
    "stiffness_source",
    "damping_source",
    "joint_map_source",
    "damping_fallback_source",
]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="校验策略部署交接元数据")
    parser.add_argument("--policy-id", default="example_base_velocity_policy")
    parser.add_argument("--motion", default="")
    parser.add_argument("--config", default="")
    parser.add_argument("--expect-standard23", action="store_true")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    print("Deploy handoff validation template.")
    print(f"policy_id: {args.policy_id}")
    if args.motion:
        print(f"motion: {args.motion}")
    if args.config:
        print(f"config: {args.config}")
    if args.expect_standard23:
        print("joint_contract: standard23")
    print(
        "SCOPE: metadata checklist only; this command does not prove deploy readiness yet."
    )
    print("Required fields:")
    for field in REQUIRED_HANDOFF_FIELDS:
        print(f"- {field}")


if __name__ == "__main__":
    main()
