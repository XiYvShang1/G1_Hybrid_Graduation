"""Script to play an ONNX policy inside the MuJoCo environment."""

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import onnxruntime as ort
import torch
import tyro

from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import RslRlVecEnvWrapper
from mjlab.tasks.registry import list_tasks, load_env_cfg, load_rl_cfg
from mjlab.tasks.tracking.mdp import MotionCommandCfg
from mjlab.utils.torch import configure_torch_backends
from mjlab.viewer import NativeMujocoViewer, ViserPlayViewer


@dataclass(frozen=True)
class PlayOnnxConfig:
  onnx_file: str
  motion_file: str | None = None
  num_envs: int | None = None
  device: str | None = None
  viewer: Literal["auto", "native", "viser"] = "auto"
  no_terminations: bool = False


class OnnxPolicy:
  def __init__(self, onnx_file: str, device: str):
    available = ort.get_available_providers()
    providers = ["CPUExecutionProvider"]
    if device.startswith("cuda") and "CUDAExecutionProvider" in available:
      providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    self.session = ort.InferenceSession(onnx_file, providers=providers)
    self.input_name = self.session.get_inputs()[0].name
    self.output_name = self.session.get_outputs()[0].name
    print(f"[INFO]: ONNX providers: {self.session.get_providers()}")

  def __call__(self, obs) -> torch.Tensor:
    actor_obs = obs["actor"] if hasattr(obs, "keys") else obs
    obs_np = actor_obs.detach().to("cpu", dtype=torch.float32).numpy()
    actions = self.session.run([self.output_name], {self.input_name: obs_np})[0]
    return torch.from_numpy(np.asarray(actions, dtype=np.float32)).to(actor_obs.device)


def run_play(task_id: str, cfg: PlayOnnxConfig):
  configure_torch_backends()

  device = cfg.device or ("cuda:0" if torch.cuda.is_available() else "cpu")
  env_cfg = load_env_cfg(task_id, play=True)
  agent_cfg = load_rl_cfg(task_id)

  if cfg.no_terminations:
    env_cfg.terminations = {}
    print("[INFO]: Terminations disabled")

  is_tracking_task = "motion" in env_cfg.commands and isinstance(
    env_cfg.commands["motion"], MotionCommandCfg
  )
  if cfg.motion_file is not None:
    if not is_tracking_task:
      raise ValueError("`--motion-file` is only valid for tracking/mimic tasks.")
    if not Path(cfg.motion_file).exists():
      raise FileNotFoundError(f"Motion file not found: {cfg.motion_file}")
    print(f"[INFO]: Using local motion file: {cfg.motion_file}")
    motion_cmd = env_cfg.commands["motion"]
    assert isinstance(motion_cmd, MotionCommandCfg)
    motion_cmd.motion_file = cfg.motion_file

  onnx_path = Path(cfg.onnx_file)
  if not onnx_path.exists():
    raise FileNotFoundError(f"ONNX file not found: {onnx_path}")
  print(f"[INFO]: Loading ONNX policy: {onnx_path}")

  if cfg.num_envs is not None:
    env_cfg.scene.num_envs = cfg.num_envs

  env = ManagerBasedRlEnv(cfg=env_cfg, device=device, render_mode=None)
  env = RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions)
  policy = OnnxPolicy(str(onnx_path), device=device)

  if cfg.viewer == "auto":
    has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    resolved_viewer = "native" if has_display else "viser"
  else:
    resolved_viewer = cfg.viewer

  if resolved_viewer == "native":
    NativeMujocoViewer(env, policy).run()
  elif resolved_viewer == "viser":
    ViserPlayViewer(env, policy).run()
  else:
    raise RuntimeError(f"Unsupported viewer backend: {resolved_viewer}")

  env.close()


def main():
  import mjlab
  import mjlab.tasks  # noqa: F401
  import src.tasks  # noqa: F401

  all_tasks = list_tasks()
  chosen_task, remaining_args = tyro.cli(
    tyro.extras.literal_type_from_choices(all_tasks),
    add_help=False,
    return_unknown_args=True,
    config=mjlab.TYRO_FLAGS,
  )

  args = tyro.cli(
    PlayOnnxConfig,
    args=remaining_args,
    default=PlayOnnxConfig(onnx_file=""),
    prog=sys.argv[0] + f" {chosen_task}",
    config=mjlab.TYRO_FLAGS,
  )
  if not args.onnx_file:
    raise ValueError("`--onnx-file` is required.")

  run_play(chosen_task, args)


if __name__ == "__main__":
  main()
