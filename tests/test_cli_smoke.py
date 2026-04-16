"""Smoke tests for CLI entrypoints in local project mode."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class CLISmokeTest(unittest.TestCase):
    def _run(self, *args: str) -> str:
        completed = subprocess.run(
            [sys.executable, "-m", "cli", *args],
            cwd=PROJECT_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError(
                f"命令失败: {' '.join(args)}\n退出码: {completed.returncode}\n输出:\n{completed.stdout}"
            )
        return completed.stdout

    def test_status_command(self) -> None:
        output = self._run("status")
        self.assertIn("项目状态概览", output)
        self.assertIn("动作资产数量", output)

    def test_show_closure_command(self) -> None:
        output = self._run("show-closure")
        self.assertIn("最小闭环报告", output)


if __name__ == "__main__":
    unittest.main()
