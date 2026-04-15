"""Motion asset metadata shared by retargeting and training pipelines."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MotionAssetContract:
    """Describes one motion asset without forcing a single storage format."""

    asset_id: str
    source_repo: str
    source_path: str
    artifact_path: str
    artifact_format: str
    expected_fields: list[str] = field(default_factory=list)
    joint_contract_id: str = ""
    consumer_pipeline: str = ""
    notes: str = ""
