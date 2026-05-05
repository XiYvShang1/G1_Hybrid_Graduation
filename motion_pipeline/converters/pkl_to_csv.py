"""把 G1 动作重定向输出的 pkl 转成 mjlab 可读取的 CSV。

目标 CSV 每行格式：
root_x, root_y, root_z, quat_x, quat_y, quat_z, quat_w, dof_0, ..., dof_22

mjlab 的 csv_to_npz.py 会把 CSV 中的 xyzw 四元数转换成内部 wxyz，所以这里保持
重定向后端和 Scipy 常见的 xyzw 顺序，不额外重排。
"""

from __future__ import annotations

import argparse
import pickle
from pathlib import Path
from typing import Any

import numpy as np


G1_23DOF_FROM_29DOF = [
    *range(0, 19),
    22,
    23,
    24,
    25,
]


def _to_numpy(value: Any) -> np.ndarray:
    """把 numpy / torch tensor / list 统一转成 numpy 数组。"""
    if hasattr(value, "detach"):
        value = value.detach().cpu().numpy()
    return np.asarray(value)


def _select_motion(payload: Any, motion_key: str | None) -> dict[str, Any]:
    """从 pkl 中取出真正的 motion 字典。

    G1 重定向后端常见保存格式是 `{filename: motion_data}`；也有一些工具会直接
    保存 motion_data。本函数兼容这两种情况。
    """
    if not isinstance(payload, dict):
        raise TypeError("pkl payload must be a dict")

    required = {"root_trans_offset", "root_rot", "dof"}
    if required.issubset(payload.keys()):
        return payload

    if motion_key is not None:
        if motion_key not in payload:
            available = ", ".join(map(str, payload.keys()))
            raise KeyError(f"motion key not found: {motion_key}; available keys: {available}")
        selected = payload[motion_key]
        if not isinstance(selected, dict):
            raise TypeError(f"selected motion is not a dict: {motion_key}")
        return selected

    candidates = [value for value in payload.values() if isinstance(value, dict) and required.issubset(value.keys())]
    if len(candidates) != 1:
        raise ValueError(f"expected exactly one motion in pkl, found {len(candidates)}; pass --motion-key")
    return candidates[0]


def load_retarget_motion(path: Path, motion_key: str | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray, float | None]:
    """读取 G1 retarget pkl，并返回 root 位置、root 四元数、关节角和 fps。"""
    with path.open("rb") as file:
        payload = pickle.load(file)

    motion = _select_motion(payload, motion_key)
    root_pos = _to_numpy(motion["root_trans_offset"]).astype(np.float64)
    root_quat_xyzw = _to_numpy(motion["root_rot"]).astype(np.float64)
    dof = _to_numpy(motion["dof"]).astype(np.float64)
    fps = motion.get("fps")
    fps_value = float(np.asarray(fps).reshape(-1)[0]) if fps is not None else None

    if root_pos.ndim != 2 or root_pos.shape[1] != 3:
        raise ValueError(f"root_trans_offset must have shape (N, 3), got {root_pos.shape}")
    if root_quat_xyzw.ndim != 2 or root_quat_xyzw.shape[1] != 4:
        raise ValueError(f"root_rot must have shape (N, 4), got {root_quat_xyzw.shape}")
    if dof.ndim != 2:
        raise ValueError(f"dof must have shape (N, D), got {dof.shape}")
    if not (root_pos.shape[0] == root_quat_xyzw.shape[0] == dof.shape[0]):
        raise ValueError("root position, root rotation, and dof frame counts do not match")

    return root_pos, root_quat_xyzw, dof, fps_value


def convert_pkl_to_csv(
    input_path: Path,
    output_path: Path,
    *,
    motion_key: str | None = None,
    robot: str = "g1_23dof",
) -> tuple[int, int, float | None]:
    """把 retarget pkl 写成 mjlab CSV，返回帧数、自由度和 fps。"""
    root_pos, root_quat_xyzw, dof, fps = load_retarget_motion(input_path, motion_key)

    if robot == "g1_23dof":
        if dof.shape[1] == 29:
            dof = dof[:, G1_23DOF_FROM_29DOF]
        elif dof.shape[1] != 23:
            raise ValueError(f"g1_23dof expects 23 dof or convertible 29 dof, got {dof.shape[1]}")
    elif robot == "g1":
        if dof.shape[1] != 29:
            raise ValueError(f"g1 expects 29 dof, got {dof.shape[1]}")
    else:
        raise ValueError(f"unsupported robot: {robot}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    csv = np.concatenate([root_pos, root_quat_xyzw, dof], axis=1)
    np.savetxt(output_path, csv, delimiter=",", fmt="%.10f")
    return csv.shape[0], dof.shape[1], fps


def build_parser() -> argparse.ArgumentParser:
    """定义命令行参数。"""
    parser = argparse.ArgumentParser(description="Convert G1 retarget pkl to mjlab CSV.")
    parser.add_argument("input", type=Path, help="Input G1 retarget pkl.")
    parser.add_argument("output", type=Path, help="Output mjlab CSV.")
    parser.add_argument("--motion-key", help="Motion key when the pkl contains multiple motions.")
    parser.add_argument("--robot", choices=["g1_23dof", "g1"], default="g1_23dof")
    return parser


def main() -> None:
    """CLI 入口。"""
    args = build_parser().parse_args()
    frames, dof, fps = convert_pkl_to_csv(args.input, args.output, motion_key=args.motion_key, robot=args.robot)
    fps_text = "unknown" if fps is None else f"{fps:g}"
    print(f"saved csv: {args.output}")
    print(f"frames={frames}, dof={dof}, fps={fps_text}")


if __name__ == "__main__":
    main()
