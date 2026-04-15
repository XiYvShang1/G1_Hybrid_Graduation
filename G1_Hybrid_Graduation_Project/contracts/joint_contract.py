"""Joint order, limits, and controllable subset contracts for Unitree G1."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class JointLimit:
    """Official or project-level joint limit in radians."""

    name: str
    lower: float
    upper: float


@dataclass(frozen=True)
class JointContract:
    """Describes a robot joint contract used by training and deployment."""

    contract_id: str
    robot_name: str
    dof_count: int
    joint_order: list[str] = field(default_factory=list)
    controllable_joints: list[str] = field(default_factory=list)
    default_pose_source: str = ""
    action_scale_source: str = ""
    limits: list[JointLimit] = field(default_factory=list)
    notes: str = ""
