"""Script to play an ONNX policy inside the MuJoCo environment."""

import json
import os
import sys
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import mujoco.viewer
import numpy as np
import onnxruntime as ort
import torch
import tyro
from viser import _messages

from mjlab.envs import ManagerBasedRlEnv
from mjlab.envs import mdp as envs_mdp
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
  command_source: Literal["viser", "fixed", "random"] = "viser"
  command_vx: float = 0.0
  command_vy: float = 0.0
  command_yaw: float = 0.0
  keyboard_step: float = 0.3
  keyboard_yaw_step: float = 0.5
  stability_push_scale: float = 1.0
  hide_reference_motion: bool = False


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


class VelocityCommandController:
  """把速度命令从随机采样切换为回放期可控输入。"""

  def __init__(
    self,
    env,
    *,
    initial_command: tuple[float, float, float],
    linear_step: float,
    yaw_step: float,
    push_scale: float,
    fixed: bool,
  ):
    self.env = env.unwrapped
    self.linear_step = linear_step
    self.yaw_step = yaw_step
    self.push_scale = push_scale
    self.fixed = fixed
    self.command = np.asarray(initial_command, dtype=np.float32)
    self._lock = threading.Lock()
    self._term = self.env.command_manager._terms.get("twist")
    self._pending_pushes = 0
    self.last_command_label = "Stop"

  def initialize(self) -> None:
    if self._term is None:
      return
    self._write_command(self.command)
    print("[INFO] 速度命令源已切换为回放控制接口。")
    print("[INFO] 浏览器 Viser: Controls -> Commands -> Twist 可直接调 vx/vy/yaw。")

  def current_command(self) -> np.ndarray:
    if self._term is None:
      return self.command
    return self._term.command[0].detach().cpu().numpy().astype(np.float32)

  def is_manual_enabled(self) -> bool:
    enabled = getattr(self._term, "_joystick_enabled", None)
    return bool(enabled is not None and enabled.value)

  def handle_shortcut(self, key_name: str) -> None:
    if key_name == "8":
      self.last_command_label = "Forward"
      self._set_command([self.linear_step, 0.0, 0.0])
    elif key_name == "2":
      self.last_command_label = "Backward"
      self._set_command([-self.linear_step, 0.0, 0.0])
    elif key_name == "4":
      self.last_command_label = "Left"
      self._set_command([0.0, self.linear_step, 0.0])
    elif key_name == "6":
      self.last_command_label = "Right"
      self._set_command([0.0, -self.linear_step, 0.0])
    elif key_name == "7":
      self.last_command_label = "Turn Left"
      self._set_command([0.0, 0.0, self.yaw_step])
    elif key_name == "9":
      self.last_command_label = "Turn Right"
      self._set_command([0.0, 0.0, -self.yaw_step])
    elif key_name == "5":
      self.last_command_label = "Stop"
      self._set_command([0.0, 0.0, 0.0])
    elif key_name == ".":
      self.last_command_label = "Push Test"
      self.queue_stability_push()

  def queue_stability_push(self) -> None:
    with self._lock:
      self._pending_pushes += 1
    print("[TEST] 抗摔稳定性测试：注入根部横向速度扰动")

  def apply_pending_disturbance(self) -> None:
    """在仿真步线程中应用浏览器按钮积累的扰动。"""
    with self._lock:
      pending_pushes = self._pending_pushes
      self._pending_pushes = 0
    for _ in range(pending_pushes):
      self._push_robot()
    if self.fixed:
      self._write_command(self.command)

  def _push_robot(self) -> None:
    env_ids = torch.arange(self.env.num_envs, device=self.env.device)
    velocity_range = {
      "x": (-0.5 * self.push_scale, 0.5 * self.push_scale),
      "y": (-0.5 * self.push_scale, 0.5 * self.push_scale),
      "z": (-0.4 * self.push_scale, 0.4 * self.push_scale),
      "roll": (-0.52 * self.push_scale, 0.52 * self.push_scale),
      "pitch": (-0.52 * self.push_scale, 0.52 * self.push_scale),
      "yaw": (-0.78 * self.push_scale, 0.78 * self.push_scale),
    }
    envs_mdp.push_by_setting_velocity(self.env, env_ids, velocity_range)

  def _set_command(self, values) -> None:
    command = np.asarray(values, dtype=np.float32)
    with self._lock:
      self.command = command
    self._write_command(command)
    print(f"[CMD] vx={command[0]:+.2f}, vy={command[1]:+.2f}, yaw={command[2]:+.2f}")

  def _write_command(self, command: np.ndarray) -> None:
    # 如果 Viser Commands/Twist 控件已经创建，同步控件值；compute() 会继续写回命令。
    enabled = getattr(self._term, "_joystick_enabled", None)
    sliders = getattr(self._term, "_joystick_sliders", None)
    if enabled is not None and sliders:
      enabled.value = True
      for slider, value in zip(sliders, command):
        slider.value = float(value)

    tensor = torch.as_tensor(command, device=self._term.vel_command_b.device)
    self._term.vel_command_b[:, :].copy_(tensor)
    self._term.command[:, :].copy_(tensor)


class ControlledVelocityPolicy:
  """在策略推理前处理浏览器控制器积累的速度命令和扰动。"""

  def __init__(self, policy: OnnxPolicy, controller: VelocityCommandController):
    self.policy = policy
    self.controller = controller

  def __call__(self, obs) -> torch.Tensor:
    self.controller.apply_pending_disturbance()
    return self.policy(obs)


class NativeVelocityKeyHandler:
  """给 MuJoCo native viewer 增加速度演示快捷键和推搡测试。"""

  def __init__(self, controller: VelocityCommandController):
    self.controller = controller

  def __call__(self, key: int) -> None:
    from mjlab.viewer.native.keys import (
      KEY_2,
      KEY_4,
      KEY_5,
      KEY_6,
      KEY_7,
      KEY_8,
      KEY_9,
      KEY_KP_2,
      KEY_KP_4,
      KEY_KP_5,
      KEY_KP_6,
      KEY_KP_7,
      KEY_KP_8,
      KEY_KP_9,
      KEY_KP_DIVIDE,
      KEY_SLASH,
    )

    key_map = {
      KEY_8: "8",
      KEY_KP_8: "8",
      KEY_2: "2",
      KEY_KP_2: "2",
      KEY_4: "4",
      KEY_KP_4: "4",
      KEY_6: "6",
      KEY_KP_6: "6",
      KEY_7: "7",
      KEY_KP_7: "7",
      KEY_9: "9",
      KEY_KP_9: "9",
      KEY_5: "5",
      KEY_KP_5: "5",
    }
    if key in key_map:
      self.controller.handle_shortcut(key_map[key])
      return
    if key in (KEY_SLASH, KEY_KP_DIVIDE):
      self.controller.queue_stability_push()


@contextmanager
def native_mujoco_panels_enabled():
  """让 mjlab native viewer 启动时显示 MuJoCo 左右控制面板。"""

  original_launch_passive = mujoco.viewer.launch_passive

  def launch_passive_with_panels(*args, **kwargs):
    kwargs["show_left_ui"] = True
    kwargs["show_right_ui"] = True
    return original_launch_passive(*args, **kwargs)

  mujoco.viewer.launch_passive = launch_passive_with_panels
  try:
    yield
  finally:
    mujoco.viewer.launch_passive = original_launch_passive


class VelocityControlViserViewer(ViserPlayViewer):
  """默认启用 Viser Twist 控件，并增加演示用快捷按钮。"""

  def __init__(self, env, policy, controller: VelocityCommandController):
    super().__init__(env, policy)
    self._velocity_controller = controller

  def setup(self) -> None:
    super().setup()
    controller = self._velocity_controller
    term = controller._term
    if term is None:
      return

    enabled = getattr(term, "_joystick_enabled", None)
    sliders = getattr(term, "_joystick_sliders", None)
    if enabled is not None:
      enabled.value = True
    if sliders:
      for slider, value in zip(sliders, controller.command):
        slider.value = float(value)

    with self._server.gui.add_folder("Velocity Demo"):
      self._keyboard_status = self._server.gui.add_html(
        self._format_keyboard_status()
      )
      buttons = [
        ("8 Forward", "8"),
        ("2 Backward", "2"),
        ("4 Left", "4"),
        ("6 Right", "6"),
        ("7 Turn Left", "7"),
        ("9 Turn Right", "9"),
        ("5 Stop", "5"),
        (". Push Test", "."),
      ]
      button_ids: dict[str, str] = {}
      for label, key in buttons:
        button = self._server.gui.add_button(label)
        button_ids[key] = button._impl.uuid

        @button.on_click
        def _(_, _key=key) -> None:
          self._velocity_controller.handle_shortcut(_key)
          self._keyboard_status.content = self._format_keyboard_status()
      self._install_browser_keyboard_shortcuts(button_ids)

  def _format_keyboard_status(self) -> str:
    controller = self._velocity_controller
    vx, vy, yaw = controller.current_command()
    mode = "手动命令" if controller.is_manual_enabled() else "自动随机命令"
    label = controller.last_command_label if controller.is_manual_enabled() else "Random"
    return (
      f"<b>当前模式：</b>{mode}<br/>"
      f"<b>当前命令：</b>{label}<br/>"
      f"<b>目标速度：</b>vx={vx:+.2f}, vy={vy:+.2f}, yaw={yaw:+.2f}<br/>"
      "<span style='font-size: 0.9em; color: #666;'>"
      "Enable 关：自动随机；Enable 开：键盘/滑条手动；. 抗扰"
      "</span>"
    )

  def sync_env_to_viewer(self) -> None:
    super().sync_env_to_viewer()
    if hasattr(self, "_keyboard_status") and self._counter % 10 == 0:
      self._keyboard_status.content = self._format_keyboard_status()

  def _install_browser_keyboard_shortcuts(self, button_ids: dict[str, str]) -> None:
    """在浏览器里监听按键，再点击隐藏按钮回传到 Python。"""
    shortcut_map = {
      "Digit8": "8",
      "Numpad8": "8",
      "ArrowUp": "8",
      "Digit2": "2",
      "Numpad2": "2",
      "ArrowDown": "2",
      "Digit4": "4",
      "Numpad4": "4",
      "ArrowLeft": "4",
      "Digit6": "6",
      "Numpad6": "6",
      "ArrowRight": "6",
      "Digit7": "7",
      "Numpad7": "7",
      "Digit9": "9",
      "Numpad9": "9",
      "Digit5": "5",
      "Numpad5": "5",
      "Period": ".",
      "NumpadDecimal": ".",
      "Delete": ".",
    }
    key_to_button_id = {
      code: button_ids[key] for code, key in shortcut_map.items() if key in button_ids
    }

    js = f"""
(() => {{
  const keyToButtonId = {json.dumps(key_to_button_id)};

  function isTypingTarget(target) {{
    if (!target) return false;
    const tag = (target.tagName || "").toLowerCase();
    return tag === "input" || tag === "textarea" || tag === "select" || target.isContentEditable;
  }}

  function hideButton(button) {{
    const wrapper = button.closest(".mantine-Box-root") || button.parentElement;
    if (wrapper) wrapper.style.display = "none";
    else button.style.display = "none";
  }}

  for (const buttonId of Object.values(keyToButtonId)) {{
    const button = document.getElementById(buttonId);
    if (button) hideButton(button);
  }}

  if (window.__g1VelocityKeyboardHandler) {{
    window.removeEventListener("keydown", window.__g1VelocityKeyboardHandler);
  }}

  window.__g1VelocityKeyboardHandler = (event) => {{
    if (isTypingTarget(event.target)) return;
    const buttonId = keyToButtonId[event.code];
    if (!buttonId) return;
    const button = document.getElementById(buttonId);
    if (!button) return;
    event.preventDefault();
    button.click();
  }};

  window.addEventListener("keydown", window.__g1VelocityKeyboardHandler);
}})();
"""
    self._server._websock_server.queue_message(_messages.RunJavascriptMessage(source=js))


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

  if cfg.hide_reference_motion and is_tracking_task:
    motion_cmd = env_cfg.commands["motion"]
    assert isinstance(motion_cmd, MotionCommandCfg)
    motion_cmd.debug_vis = False
    print("[INFO]: Reference motion visualization disabled")

  onnx_path = Path(cfg.onnx_file)
  if not onnx_path.exists():
    raise FileNotFoundError(f"ONNX file not found: {onnx_path}")
  print(f"[INFO]: Loading ONNX policy: {onnx_path}")

  if cfg.num_envs is not None:
    env_cfg.scene.num_envs = cfg.num_envs

  env = ManagerBasedRlEnv(cfg=env_cfg, device=device, render_mode=None)
  env = RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions)
  policy = OnnxPolicy(str(onnx_path), device=device)

  velocity_controller = None
  if cfg.command_source in {"viser", "fixed"} and "twist" in env.unwrapped.command_manager.active_terms:
    velocity_controller = VelocityCommandController(
      env,
      initial_command=(cfg.command_vx, cfg.command_vy, cfg.command_yaw),
      linear_step=cfg.keyboard_step,
      yaw_step=cfg.keyboard_yaw_step,
      push_scale=cfg.stability_push_scale,
      fixed=cfg.command_source == "fixed",
    )
    velocity_controller.initialize()
    policy = ControlledVelocityPolicy(policy, velocity_controller)

  if cfg.viewer == "auto":
    has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    resolved_viewer = "native" if has_display else "viser"
  else:
    resolved_viewer = cfg.viewer

  try:
    if resolved_viewer == "native":
      key_callback = (
        NativeVelocityKeyHandler(velocity_controller)
        if velocity_controller is not None
        else None
      )
      if key_callback is not None:
        print("[INFO] Native MuJoCo 快捷键: 8/2/4/6/7/9 控制速度，5 停止，/ 随机推搡。")
      with native_mujoco_panels_enabled():
        NativeMujocoViewer(env, policy, key_callback=key_callback).run()
    elif resolved_viewer == "viser":
      if velocity_controller is not None:
        VelocityControlViserViewer(env, policy, velocity_controller).run()
      else:
        ViserPlayViewer(env, policy).run()
    else:
      raise RuntimeError(f"Unsupported viewer backend: {resolved_viewer}")
  finally:
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
