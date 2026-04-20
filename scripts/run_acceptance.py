"""Run acceptance checks for the G1 hybrid project."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = PROJECT_ROOT


def _run(command: list[str], expected_substrings: list[str]) -> None:
    completed = subprocess.run(
        command,
        cwd=RUN_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    print(f"$ {' '.join(command)}")
    print(completed.stdout)
    if completed.returncode != 0:
        raise RuntimeError(
            f"命令失败，退出码 {completed.returncode}: {' '.join(command)}"
        )
    for substring in expected_substrings:
        if substring not in completed.stdout:
            raise AssertionError(f"输出缺少预期内容 {substring!r}: {' '.join(command)}")


def main() -> None:
    python = sys.executable
    commands = [
        (
            [
                python,
                "-m",
                "cli",
                "reset-example-registry",
            ],
            ["registry"],
        ),
        (
            [python, "-m", "cli", "status"],
            ["example_motion_asset", "example_skill_policy"],
        ),
        (
            [python, "-m", "unittest", "tests.test_cli_smoke"],
            ["OK"],
        ),
        (
            [python, "-m", "cli", "check-paths"],
            ["g1_base_velocity_flat", "g1_skill_motion_tracking"],
        ),
        (
            [python, "-m", "cli", "show-closure"],
            ["最小闭环", "example_base_velocity_policy"],
        ),
        (
            [
                python,
                "-m",
                "cli",
                "add-motion",
                "--config",
                str(PROJECT_ROOT / "configs" / "assets" / "example_motion_asset.yaml"),
            ],
            ["asset_id: example_motion_asset"],
        ),
        (
            [
                python,
                "-m",
                "cli",
                "add-task",
                "--config",
                str(
                    PROJECT_ROOT
                    / "configs"
                    / "tasks"
                    / "example_base_velocity_task.yaml"
                ),
            ],
            ["task_id: g1_base_velocity_flat"],
        ),
        (
            [
                python,
                "-m",
                "cli",
                "add-policy",
                "--config",
                str(
                    PROJECT_ROOT / "configs" / "policies" / "example_policy_bundle.yaml"
                ),
            ],
            ["policy_id: example_base_velocity_policy"],
        ),
        (
            [python, "-m", "pipelines.build_motion_asset"],
            ["registered_to", "motion_domain"],
        ),
        (
            [python, "-m", "pipelines.train_base_policy"],
            ["registered_to", "base_domain"],
        ),
        (
            [python, "-m", "pipelines.train_skill_policy"],
            ["registered_to", "skill_domain"],
        ),
        (
            [
                python,
                "-m",
                "cli",
                "workflow",
                "--config",
                str(
                    PROJECT_ROOT
                    / "configs"
                    / "workflows"
                    / "example_orchestration.yaml"
                ),
            ],
            ["stage: motion", "stage: base", "stage: skill", "status: planned"],
        ),
        (
            [
                python,
                "-m",
                "cli",
                "workflow",
                "--config",
                str(
                    PROJECT_ROOT
                    / "configs"
                    / "workflows"
                    / "example_orchestration.yaml"
                ),
                "--execute",
                "--stages",
                "motion",
            ],
            ["stage: motion", "status: success", "expected_output:"],
        ),
        (
            [python, "-m", "cli", "status"],
            ["动作资产数量: 1", "训练任务数量: 2", "策略产物数量: 2"],
        ),
    ]

    for command, expected in commands:
        _run(command, expected)

    print("ACCEPTANCE PASSED")


if __name__ == "__main__":
    main()
