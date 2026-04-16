"""Registry loading and summary helpers for the hybrid graduation project."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from path_utils import resolve_workspace_path


PROJECT_ROOT = Path(__file__).resolve().parent
REGISTRY_FILENAMES = {
    "motions": "motion_registry.yaml",
    "tasks": "task_registry.yaml",
    "policies": "policy_registry.yaml",
}
REGISTRY_KEY_FIELDS = {
    "motions": "asset_id",
    "tasks": "task_id",
    "policies": "policy_id",
}


@dataclass(frozen=True)
class RegistryBundle:
    """Loaded registry content with convenient typed accessors."""

    motions: list[dict[str, Any]]
    tasks: list[dict[str, Any]]
    policies: list[dict[str, Any]]

    def count_summary(self) -> dict[str, int]:
        return {
            "motions": len(self.motions),
            "tasks": len(self.tasks),
            "policies": len(self.policies),
        }


def _load_yaml_file(file_path: Path) -> dict[str, Any]:
    with file_path.open("r", encoding="utf-8") as file:
        content = yaml.safe_load(file) or {}
    if not isinstance(content, dict):
        raise ValueError(f"YAML 顶层必须是字典: {file_path}")
    return content


def _write_yaml_file(file_path: Path, payload: dict[str, Any]) -> None:
    with file_path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(payload, file, allow_unicode=True, sort_keys=False)


def load_registry_bundle(project_root: Path | None = None) -> RegistryBundle:
    root = project_root or PROJECT_ROOT
    registry_dir = root / "registry"

    motion_data = _load_yaml_file(registry_dir / "motion_registry.yaml")
    task_data = _load_yaml_file(registry_dir / "task_registry.yaml")
    policy_data = _load_yaml_file(registry_dir / "policy_registry.yaml")

    motions = motion_data.get("motions", [])
    tasks = task_data.get("tasks", [])
    policies = policy_data.get("policies", [])

    if (
        not isinstance(motions, list)
        or not isinstance(tasks, list)
        or not isinstance(policies, list)
    ):
        raise ValueError("registry 文件中的 motions/tasks/policies 必须是列表")

    return RegistryBundle(motions=motions, tasks=tasks, policies=policies)


def load_yaml_config(config_path: Path) -> dict[str, Any]:
    payload = _load_yaml_file(config_path)
    return payload


def _registry_file_path(project_root: Path, bucket: str) -> Path:
    if bucket not in REGISTRY_FILENAMES:
        raise ValueError(f"未知 registry bucket: {bucket}")
    return project_root / "registry" / REGISTRY_FILENAMES[bucket]


def upsert_registry_item(project_root: Path, bucket: str, item: dict[str, Any]) -> Path:
    file_path = _registry_file_path(project_root, bucket)
    payload = _load_yaml_file(file_path)
    current_items = payload.get(bucket, [])
    if not isinstance(current_items, list):
        raise ValueError(f"{file_path} 中的 {bucket} 必须是列表")

    key_field = REGISTRY_KEY_FIELDS[bucket]
    item_key = item.get(key_field)
    if not item_key:
        raise ValueError(f"注册项缺少主键字段 {key_field}: {item}")

    replaced = False
    for index, existing in enumerate(current_items):
        if isinstance(existing, dict) and existing.get(key_field) == item_key:
            current_items[index] = item
            replaced = True
            break

    if not replaced:
        current_items.append(item)

    payload[bucket] = current_items
    _write_yaml_file(file_path, payload)
    return file_path


def reset_registry_to_examples(project_root: Path) -> list[Path]:
    motions = [
        load_yaml_config(
            project_root / "configs" / "assets" / "example_motion_asset.yaml"
        )
    ]
    tasks = [
        load_yaml_config(
            project_root / "configs" / "tasks" / "example_base_velocity_task.yaml"
        ),
        load_yaml_config(
            project_root / "configs" / "tasks" / "example_skill_tracking_task.yaml"
        ),
    ]
    policies = [
        load_yaml_config(
            project_root / "configs" / "policies" / "example_policy_bundle.yaml"
        ),
        load_yaml_config(
            project_root / "configs" / "policies" / "example_skill_policy_bundle.yaml"
        ),
    ]

    motion_file = _registry_file_path(project_root, "motions")
    task_file = _registry_file_path(project_root, "tasks")
    policy_file = _registry_file_path(project_root, "policies")

    _write_yaml_file(motion_file, {"motions": motions})
    _write_yaml_file(task_file, {"tasks": tasks})
    _write_yaml_file(policy_file, {"policies": policies})

    return [motion_file, task_file, policy_file]


def format_registry_status(bundle: RegistryBundle) -> str:
    lines = [
        "G1 混合毕设项目状态概览",
        "=" * 24,
        f"动作资产数量: {len(bundle.motions)}",
        f"训练任务数量: {len(bundle.tasks)}",
        f"策略产物数量: {len(bundle.policies)}",
        "",
        "动作资产:",
    ]

    for motion in bundle.motions:
        lines.append(
            f"- {motion.get('asset_id', 'unknown')} | {motion.get('source_repo', 'unknown')} -> {motion.get('consumer_pipeline', 'unknown')}"
        )

    lines.append("")
    lines.append("训练任务:")
    for task in bundle.tasks:
        lines.append(
            f"- {task.get('task_id', 'unknown')} | {task.get('task_type', 'unknown')} | {task.get('source_repo', 'unknown')}"
        )

    lines.append("")
    lines.append("策略产物:")
    for policy in bundle.policies:
        lines.append(
            f"- {policy.get('policy_id', 'unknown')} | {policy.get('policy_type', 'unknown')} | {policy.get('status', 'unknown')}"
        )

    return "\n".join(lines)


def _resolve_from_project_root(project_root: Path, raw_path: str) -> Path:
    return resolve_workspace_path(project_root, raw_path)


def collect_path_checks(
    project_root: Path, bundle: RegistryBundle
) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []

    for motion in bundle.motions:
        for field in ("source_path", "artifact_path"):
            raw_path = motion.get(field)
            if raw_path:
                resolved = _resolve_from_project_root(project_root, raw_path)
                checks.append(
                    {
                        "kind": "motion",
                        "item_id": motion.get("asset_id", "unknown"),
                        "field": field,
                        "raw_path": raw_path,
                        "resolved_path": str(resolved),
                        "exists": "yes" if resolved.exists() else "no",
                    }
                )

    for task in bundle.tasks:
        raw_path = task.get("upstream_entry")
        if raw_path:
            resolved = _resolve_from_project_root(project_root, raw_path)
            checks.append(
                {
                    "kind": "task",
                    "item_id": task.get("task_id", "unknown"),
                    "field": "upstream_entry",
                    "raw_path": raw_path,
                    "resolved_path": str(resolved),
                    "exists": "yes" if resolved.exists() else "no",
                }
            )

    for policy in bundle.policies:
        raw_path = policy.get("artifact_path")
        if raw_path:
            resolved = _resolve_from_project_root(project_root, raw_path)
            checks.append(
                {
                    "kind": "policy",
                    "item_id": policy.get("policy_id", "unknown"),
                    "field": "artifact_path",
                    "raw_path": raw_path,
                    "resolved_path": str(resolved),
                    "exists": "yes" if resolved.exists() else "no",
                }
            )

    return checks


def format_path_checks(checks: list[dict[str, str]]) -> str:
    lines = ["路径检查结果", "=" * 16]
    for check in checks:
        lines.append(
            f"- [{check['exists']}] {check['kind']}:{check['item_id']} | {check['field']} | {check['raw_path']}"
        )
    return "\n".join(lines)


def build_closure_report(bundle: RegistryBundle) -> str:
    lines = [
        "G1 混合毕设项目最小闭环报告",
        "=" * 28,
        "闭环主线:",
        "1. 动作资产：GVHMR2PBHC -> PBHC 兼容 motion asset",
        "2. 基础任务：unitree_rl_mjlab velocity task",
        "3. 技能任务：PBHC motion tracking task",
        "4. 基础策略：unitree_rl_mjlab policy artifact",
        "5. 技能策略：PBHC skill policy artifact",
        "",
    ]

    if bundle.motions:
        motion = bundle.motions[0]
        lines.append(f"当前示例动作资产: {motion.get('asset_id', 'unknown')}")
        lines.append(f"- 来源仓库: {motion.get('source_repo', 'unknown')}")
        lines.append(f"- 消费链路: {motion.get('consumer_pipeline', 'unknown')}")
        lines.append("")

    if bundle.tasks:
        lines.append("当前示例任务:")
        for task in bundle.tasks:
            lines.append(
                f"- {task.get('task_id', 'unknown')} | {task.get('task_type', 'unknown')} | {task.get('source_repo', 'unknown')}"
            )
        lines.append("")

    if bundle.policies:
        lines.append("当前示例策略:")
        for policy in bundle.policies:
            lines.append(
                f"- {policy.get('policy_id', 'unknown')} | {policy.get('policy_type', 'unknown')} | deploy_contract={policy.get('deploy_contract_id', 'unknown')}"
            )

    return "\n".join(lines)
