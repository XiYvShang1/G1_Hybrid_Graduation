"""Path resolution helpers for project-local and upstream workspace files."""

from __future__ import annotations

import os
from pathlib import Path

UPSTREAM_REPOS = ("PBHC", "GVHMR2PBHC", "unitree_rl_mjlab")


def detect_workspace_root(project_root: Path) -> Path:
    """Detect workspace root that contains upstream repos.

    Priority:
    1) UNITREE_WORKSPACE_ROOT env
    2) <project_root>/..
    3) <project_root>/../Unitree_G1
    4) /mnt/f/Unitree_G1
    """
    env_root = os.environ.get("UNITREE_WORKSPACE_ROOT")
    candidates: list[Path] = []
    if env_root:
        candidates.append(Path(env_root).expanduser().resolve())

    parent = project_root.resolve().parent
    candidates.append(parent)
    candidates.append(parent / "Unitree_G1")
    candidates.append(Path("/mnt/f/Unitree_G1"))

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if not candidate.exists():
            continue
        if any((candidate / repo).exists() for repo in UPSTREAM_REPOS):
            return candidate

    return parent


def resolve_workspace_path(project_root: Path, raw_path: str) -> Path:
    """Resolve a path from config/registry.

    - normal relative paths => relative to project_root
    - '../PBHC/...', '../GVHMR2PBHC/...', '../unitree_rl_mjlab/...' =>
      relative to detected workspace root
    """
    path_obj = Path(str(raw_path))
    if path_obj.is_absolute():
        return path_obj

    normalized = str(raw_path).replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    for repo in UPSTREAM_REPOS:
        token = f"../{repo}/"
        if normalized.startswith(token):
            workspace_root = detect_workspace_root(project_root)
            suffix = normalized[len(token) :]
            return (workspace_root / repo / suffix).resolve()
        if normalized == f"../{repo}":
            workspace_root = detect_workspace_root(project_root)
            return (workspace_root / repo).resolve()

    return (project_root / path_obj).resolve()
