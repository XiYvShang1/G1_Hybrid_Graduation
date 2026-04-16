"""Policy artifact metadata for base locomotion and skill policies."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PolicyContract:
    """Describes a trained policy artifact and its semantic dependencies."""

    policy_id: str
    policy_type: str
    source_repo: str
    task_id: str
    artifact_path: str
    config_paths: list[str] = field(default_factory=list)
    motion_asset_id: str = ""
    joint_contract_id: str = ""
    deploy_contract_id: str = ""
    status: str = "registered"
    notes: str = ""
