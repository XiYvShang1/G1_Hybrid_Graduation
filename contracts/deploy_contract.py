"""Deployment handoff metadata for policy-to-hybrid-command recovery."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DeployContract:
    """Describes the minimum handoff required before deployment validation."""

    deploy_contract_id: str
    policy_id: str
    obs_layout_source: str
    action_scale_source: str
    default_pose_source: str
    stiffness_source: str
    damping_source: str
    joint_map_source: str
    command_mode: str = "position"
    damping_fallback_source: str = ""
    safety_notes: list[str] = field(default_factory=list)
