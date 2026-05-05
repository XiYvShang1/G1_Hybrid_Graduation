"""把 GVHMR demo 输出转换为项目统一的 SMPL 动作 npz。

输出字段与后续 G1 动作重定向保持一致：
- betas: (10,)
- gender: "neutral"
- poses: (F, 66)，root global_orient + 21 个 body joints 的 axis-angle
- trans: (F, 3)
- mocap_framerate: 30
"""

from __future__ import annotations

import argparse
import pickle
from pathlib import Path
from typing import Any

import numpy as np


def _to_numpy(value: Any) -> np.ndarray:
    """把 torch tensor / numpy / list 统一成 numpy。"""
    if hasattr(value, "detach"):
        value = value.detach().cpu().numpy()
    return np.asarray(value)


def _first_frame_or_zeros(value: Any, width: int) -> np.ndarray:
    """GVHMR 的 betas 有时带帧维度，这里取第一帧作为统一体型参数。"""
    if value is None:
        return np.zeros(width, dtype=np.float32)
    arr = _to_numpy(value).astype(np.float32)
    if arr.ndim == 0:
        return np.full(width, float(arr), dtype=np.float32)
    if arr.ndim >= 2:
        arr = arr.reshape(-1, arr.shape[-1])[0]
    arr = arr.reshape(-1)
    if arr.shape[0] >= width:
        return arr[:width].astype(np.float32)
    padded = np.zeros(width, dtype=np.float32)
    padded[: arr.shape[0]] = arr
    return padded


def convert_gvhmr_to_smpl(input_path: Path, output_path: Path, *, fps: int = 30, frame: str = "global") -> None:
    """读取 GVHMR hmr4d_results.pt 或整合版导出的 pkl，写出标准 SMPL npz。"""
    if input_path.suffix.lower() == ".pkl":
        with input_path.open("rb") as file:
            result = pickle.load(file)
    else:
        import torch

        result = torch.load(input_path, map_location="cpu")
    params_key = "smpl_params_global" if frame == "global" else "smpl_params_incam"
    if params_key not in result:
        raise KeyError(f"{params_key} not found in {input_path}")
    params = result[params_key]

    global_orient = _to_numpy(params["global_orient"]).astype(np.float32).reshape(-1, 3)
    body_pose = _to_numpy(params["body_pose"]).astype(np.float32).reshape(global_orient.shape[0], -1)
    trans = _to_numpy(params.get("transl", params.get("trans"))).astype(np.float32).reshape(global_orient.shape[0], 3)

    if body_pose.shape[1] < 63:
        raise ValueError(f"body_pose needs at least 63 values per frame, got {body_pose.shape}")
    poses = np.concatenate([global_orient, body_pose[:, :63]], axis=1).astype(np.float32)
    betas = _first_frame_or_zeros(params.get("betas"), 10)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        output_path,
        betas=betas,
        gender="neutral",
        poses=poses,
        trans=trans,
        mocap_framerate=np.array(fps, dtype=np.float32),
    )
    print(f"saved smpl npz: {output_path}")
    print(f"frames={poses.shape[0]}, fps={fps}, frame={frame}")


def build_parser() -> argparse.ArgumentParser:
    """定义命令行参数。"""
    parser = argparse.ArgumentParser(description="Convert GVHMR hmr4d_results.pt to standard SMPL npz.")
    parser.add_argument("input", type=Path, help="Input hmr4d_results.pt.")
    parser.add_argument("output", type=Path, help="Output standard SMPL npz.")
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--frame", choices=["global", "incam"], default="global")
    return parser


def main() -> None:
    """CLI 入口。"""
    args = build_parser().parse_args()
    convert_gvhmr_to_smpl(args.input, args.output, fps=args.fps, frame=args.frame)


if __name__ == "__main__":
    main()
