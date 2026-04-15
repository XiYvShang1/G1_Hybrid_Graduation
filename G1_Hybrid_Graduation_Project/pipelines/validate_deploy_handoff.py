"""Validate whether a registered policy has enough deployment metadata."""

REQUIRED_HANDOFF_FIELDS = [
    "obs_layout_source",
    "action_scale_source",
    "default_pose_source",
    "stiffness_source",
    "damping_source",
    "joint_map_source",
    "damping_fallback_source",
]


def main() -> None:
    print("Deploy handoff validation template.")
    print(
        "SCOPE: metadata checklist only; this command does not prove deploy readiness yet."
    )
    print("Required fields:")
    for field in REQUIRED_HANDOFF_FIELDS:
        print(f"- {field}")


if __name__ == "__main__":
    main()
