"""Export and register trained policy bundles."""

from __future__ import annotations

import argparse


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="导出策略产物登记包")
    parser.add_argument("--policy-id", default="example_base_velocity_policy")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    print("Policy bundle export template.")
    print(f"policy_id: {args.policy_id}")
    print(
        "SCOPE: metadata template only; this command does not export a real policy artifact yet."
    )
    print(
        "Next step: collect policy artifact, config files, joint contract, and deploy handoff metadata."
    )


if __name__ == "__main__":
    main()
