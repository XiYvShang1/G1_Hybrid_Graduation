"""Process a motion asset into the project runtime area."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="处理并登记项目内动作资产")
    parser.add_argument("source", type=Path, help="输入动作文件")
    parser.add_argument("--output", type=Path, required=True, help="输出动作文件")
    parser.add_argument("--fix-part", default="lower", help="保留的动作修正语义标签")
    parser.add_argument("--split-index", type=int, default=12, help="上下身切分索引")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    source = args.source.resolve()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    if not source.exists():
        raise FileNotFoundError(f"动作源文件不存在: {source}")

    shutil.copyfile(source, output)
    print("Motion asset processed")
    print(f"source: {source}")
    print(f"output: {output}")
    print(f"fix_part: {args.fix_part}")
    print(f"split_index: {args.split_index}")


if __name__ == "__main__":
    main()
