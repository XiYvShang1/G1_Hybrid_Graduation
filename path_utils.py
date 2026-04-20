"""Path resolution helpers for project-local files."""

from __future__ import annotations

from pathlib import Path


def resolve_workspace_path(project_root: Path, raw_path: str) -> Path:
    """Resolve a path from config/registry.

    Absolute paths are returned as-is. Relative paths are resolved inside the
    project root so configs remain portable and free of external repository names.
    """
    path_obj = Path(str(raw_path))
    if path_obj.is_absolute():
        return path_obj
    return (project_root / path_obj).resolve()
