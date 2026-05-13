"""Lightweight MuJoCo deployment player for the G1 23DoF velocity ONNX policy."""

from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

import glfw
import mujoco
import mujoco.viewer
import numpy as np
import onnxruntime as ort

ENGINE_ROOT = Path(__file__).resolve().parents[1]
if str(ENGINE_ROOT) not in sys.path:
  sys.path.insert(0, str(ENGINE_ROOT))

from src.assets.robots.unitree_g1.g1_23dof_constants import (  # noqa: E402
  G1_23DOF_ACTION_SCALE,
  HOME_KEYFRAME,
  DAMPING_4010,
  DAMPING_5020,
  DAMPING_7520_14,
  DAMPING_7520_22,
  STIFFNESS_4010,
  STIFFNESS_5020,
  STIFFNESS_7520_14,
  STIFFNESS_7520_22,
  get_g1_23dof_robot_cfg,
)
from mjlab.entity.entity import Entity  # noqa: E402


POLICY_JOINT_NAMES = (
  "left_hip_pitch_joint",
  "left_hip_roll_joint",
  "left_hip_yaw_joint",
  "left_knee_joint",
  "left_ankle_pitch_joint",
  "left_ankle_roll_joint",
  "right_hip_pitch_joint",
  "right_hip_roll_joint",
  "right_hip_yaw_joint",
  "right_knee_joint",
  "right_ankle_pitch_joint",
  "right_ankle_roll_joint",
  "waist_yaw_joint",
  "left_shoulder_pitch_joint",
  "left_shoulder_roll_joint",
  "left_shoulder_yaw_joint",
  "left_elbow_joint",
  "left_wrist_roll_joint",
  "right_shoulder_pitch_joint",
  "right_shoulder_roll_joint",
  "right_shoulder_yaw_joint",
  "right_elbow_joint",
  "right_wrist_roll_joint",
)

DEFAULT_XML = None
DEFAULT_ONNX = (
  ENGINE_ROOT
  / "deploy"
  / "robots"
  / "g1_23dof"
  / "config"
  / "policy"
  / "velocity"
  / "v0"
  / "exported"
  / "policy.onnx"
)

def quat_conjugate(q: np.ndarray) -> np.ndarray:
  return np.array([q[0], -q[1], -q[2], -q[3]], dtype=np.float64)


def quat_mul(a: np.ndarray, b: np.ndarray) -> np.ndarray:
  aw, ax, ay, az = a
  bw, bx, by, bz = b
  return np.array(
    [
      aw * bw - ax * bx - ay * by - az * bz,
      aw * bx + ax * bw + ay * bz - az * by,
      aw * by - ax * bz + ay * bw + az * bx,
      aw * bz + ax * by - ay * bx + az * bw,
    ],
    dtype=np.float64,
  )


def rotate_inverse(q_wxyz: np.ndarray, vec: np.ndarray) -> np.ndarray:
  q = q_wxyz / np.linalg.norm(q_wxyz)
  vq = np.array([0.0, vec[0], vec[1], vec[2]], dtype=np.float64)
  return quat_mul(quat_mul(quat_conjugate(q), vq), q)[1:]


def action_scale_for_joint(joint_name: str) -> float:
  import re

  for pattern, scale in G1_23DOF_ACTION_SCALE.items():
    if re.fullmatch(pattern, joint_name):
      return float(scale)
  return 0.05


def default_joint_positions(model: mujoco.MjModel) -> np.ndarray:
  default_q = np.zeros(model.nv - 6, dtype=np.float32)
  for expr, value in HOME_KEYFRAME.joint_pos.items():
    import re

    for i in range(1, model.njnt):
      name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, i)
      if name and re.fullmatch(expr, name):
        default_q[int(model.jnt_dofadr[i]) - 6] = float(value)
  return default_q


class OnnxPolicy:
  def __init__(self, onnx_file: Path):
    self.session = ort.InferenceSession(str(onnx_file), providers=["CPUExecutionProvider"])
    self.input_name = self.session.get_inputs()[0].name
    self.output_name = self.session.get_outputs()[0].name
    print(f"[INFO] ONNX loaded: {onnx_file}")
    print(f"[INFO] ONNX providers: {self.session.get_providers()}")

  def __call__(self, obs: np.ndarray) -> np.ndarray:
    action = self.session.run([self.output_name], {self.input_name: obs.astype(np.float32)})[0]
    return np.asarray(action[0], dtype=np.float32)


class VelocityLitePlayer:
  def __init__(self, args: argparse.Namespace):
    self.args = args
    self.model = self.load_model(args.xml_file)
    self.data = mujoco.MjData(self.model)
    self.model.opt.timestep = args.sim_dt
    self.policy = OnnxPolicy(args.onnx_file)
    self.default_q = default_joint_positions(self.model)
    self.command = np.array([args.vx, args.vy, args.yaw], dtype=np.float32)
    self.last_action = np.zeros(len(POLICY_JOINT_NAMES), dtype=np.float32)
    self.policy_qadr = np.array(
      [self.model.jnt_qposadr[self.joint_id(name)] for name in POLICY_JOINT_NAMES],
      dtype=np.int32,
    )
    self.policy_dadr = np.array(
      [self.model.jnt_dofadr[self.joint_id(name)] for name in POLICY_JOINT_NAMES],
      dtype=np.int32,
    )
    self.policy_act_ids = np.array(
      [self.actuator_id(name) for name in POLICY_JOINT_NAMES],
      dtype=np.int32,
    )
    self.policy_default_q = self.default_q[self.policy_dadr - 6]
    self.action_scale = np.array(
      [action_scale_for_joint(name) for name in POLICY_JOINT_NAMES],
      dtype=np.float32,
    )
    self.kp, self.kd, self.tau_limit = self.make_pd_gains()
    self.uses_position_actuators = self.detect_position_actuators()
    self.anchor_body_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "torso_link")
    self.mode = "LOCO"
    print(f"[INFO] model nq/nv/nu: {self.model.nq}/{self.model.nv}/{self.model.nu}")
    print(f"[INFO] control mode: {'position target' if self.uses_position_actuators else 'manual torque PD'}")
    self.reset()

  def load_model(self, xml_file: Path | None) -> mujoco.MjModel:
    if xml_file is not None:
      print(f"[INFO] loading external MuJoCo XML: {xml_file}")
      return mujoco.MjModel.from_xml_path(str(xml_file))

    # Use the same robot factory as the mjlab training environment.  This avoids
    # the old demo XML, which contains 29 actuators even though the policy is 23DoF.
    print("[INFO] building 23DoF model from training robot config")
    spec = Entity(get_g1_23dof_robot_cfg()).spec
    spec.visual.headlight.diffuse = [0.6, 0.6, 0.6]
    spec.visual.headlight.ambient = [0.1, 0.1, 0.1]
    spec.visual.headlight.specular = [0.9, 0.9, 0.9]
    spec.visual.rgba.haze = [0.15, 0.25, 0.35, 1.0]
    spec.visual.global_.azimuth = -140
    spec.visual.global_.elevation = -20
    spec.add_material(name="floor_collision", rgba=[0.0, 0.0, 0.0, 0.0])
    spec.add_material(name="tile_dark", rgba=[0.1, 0.2, 0.3, 1.0])
    spec.add_material(name="tile_light", rgba=[0.2, 0.3, 0.4, 1.0])
    spec.worldbody.add_geom(
      name="floor",
      type=mujoco.mjtGeom.mjGEOM_PLANE,
      size=[0.0, 0.0, 0.05],
      condim=3,
      friction=[1.2, 0.02, 0.001],
      material="floor_collision",
    )

    # Native MuJoCo sometimes ignores programmatic checker textures on MjSpec
    # materials.  Visual-only tiles make the floor match the 29DoF demo reliably.
    tile_size = 0.7
    tile_count = 32
    origin = -tile_size * tile_count / 2.0
    for ix in range(tile_count):
      for iy in range(tile_count):
        material = "tile_light" if (ix + iy) % 2 == 0 else "tile_dark"
        spec.worldbody.add_geom(
          name=f"floor_tile_{ix}_{iy}",
          type=mujoco.mjtGeom.mjGEOM_BOX,
          pos=[
            origin + (ix + 0.5) * tile_size,
            origin + (iy + 0.5) * tile_size,
            -0.002,
          ],
          size=[tile_size / 2.0, tile_size / 2.0, 0.001],
          contype=0,
          conaffinity=0,
          material=material,
        )
    spec.worldbody.add_light(
      name="key_light",
      pos=[1.0, 0.0, 3.5],
      dir=[0.0, 0.0, -1.0],
      type=mujoco.mjtLightType.mjLIGHT_DIRECTIONAL,
    )
    return spec.compile()

  def joint_id(self, name: str) -> int:
    joint_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, name)
    if joint_id < 0:
      raise ValueError(f"Joint not found: {name}")
    return joint_id

  def actuator_id(self, name: str) -> int:
    actuator_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, name)
    if actuator_id < 0 and name.endswith("_joint"):
      actuator_id = mujoco.mj_name2id(
        self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, name.removesuffix("_joint")
      )
    if actuator_id < 0:
      raise ValueError(f"Actuator not found: {name}")
    return actuator_id

  def detect_position_actuators(self) -> bool:
    """Return True when MuJoCo actuators already implement position servo PD."""
    if self.model.nu == 0:
      return False
    selected = self.policy_act_ids
    return bool(np.all(self.model.actuator_biastype[selected] == mujoco.mjtBias.mjBIAS_AFFINE))

  def make_pd_gains(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    ctrl = self.model.actuator_ctrlrange.copy()
    tau_limit = np.maximum(np.abs(ctrl[:, 0]), np.abs(ctrl[:, 1])).astype(np.float32)
    kp = np.full(self.model.nu, self.args.kp, dtype=np.float32)
    kd = np.full(self.model.nu, self.args.kd, dtype=np.float32)
    for i in range(self.model.nu):
      name = mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, i) or ""
      if "hip_pitch" in name or "hip_yaw" in name or name == "waist_yaw":
        kp[i], kd[i] = STIFFNESS_7520_14, DAMPING_7520_14
      elif "hip_roll" in name or "knee" in name:
        kp[i], kd[i] = STIFFNESS_7520_22, DAMPING_7520_22
      elif "ankle" in name:
        kp[i], kd[i] = STIFFNESS_5020 * 2.0, DAMPING_5020 * 2.0
      elif "wrist_pitch" in name or "wrist_yaw" in name:
        kp[i], kd[i] = STIFFNESS_4010, DAMPING_4010
      elif "shoulder" in name or "elbow" in name or "wrist_roll" in name:
        kp[i], kd[i] = STIFFNESS_5020, DAMPING_5020
    return kp, kd, tau_limit

  def reset(self):
    self.data.qpos[:] = 0.0
    self.data.qvel[:] = 0.0
    self.data.qpos[:3] = np.array(HOME_KEYFRAME.pos, dtype=np.float64)
    self.data.qpos[3:7] = np.array([1.0, 0.0, 0.0, 0.0])
    self.data.qpos[7:] = self.default_q
    self.last_action[:] = 0.0
    self.mode = "LOCO"
    mujoco.mj_forward(self.model, self.data)

  def build_observation(self, step_count: int) -> np.ndarray:
    quat = self.data.qpos[3:7].copy()
    base_ang_vel_b = rotate_inverse(quat, self.data.qvel[3:6])
    gravity_b = rotate_inverse(quat, np.array([0.0, 0.0, -1.0]))
    q = self.data.qpos[self.policy_qadr].astype(np.float32)
    dq = self.data.qvel[self.policy_dadr].astype(np.float32)
    phase = np.zeros(2, dtype=np.float32)
    if np.linalg.norm(self.command) >= 0.1:
      t = step_count * self.args.control_dt
      global_phase = (t % self.args.gait_period) / self.args.gait_period
      phase[:] = [math.sin(global_phase * math.tau), math.cos(global_phase * math.tau)]
    obs = np.concatenate(
      [
        base_ang_vel_b.astype(np.float32),
        gravity_b.astype(np.float32),
        self.command.astype(np.float32),
        phase,
        q - self.policy_default_q,
        dq,
        self.last_action,
      ]
    )
    return obs[None, :]

  def apply_action(self, action: np.ndarray):
    target_policy_q = self.policy_default_q + action * self.action_scale
    if self.uses_position_actuators:
      low = self.model.actuator_ctrlrange[self.policy_act_ids, 0]
      high = self.model.actuator_ctrlrange[self.policy_act_ids, 1]
      self.data.ctrl[:] = 0.0
      self.data.ctrl[self.policy_act_ids] = np.clip(target_policy_q, low, high)
      self.last_action[:] = action
      return

    q = self.data.qpos[self.policy_qadr]
    dq = self.data.qvel[self.policy_dadr]
    tau = self.kp[self.policy_act_ids] * (target_policy_q - q) - self.kd[self.policy_act_ids] * dq
    tau = np.clip(tau, -self.tau_limit[self.policy_act_ids], self.tau_limit[self.policy_act_ids])
    self.data.ctrl[:] = 0.0
    self.data.ctrl[self.policy_act_ids] = tau
    self.last_action[:] = action

  def push(self):
    self.data.qvel[0] += np.random.uniform(-self.args.push_linear, self.args.push_linear)
    self.data.qvel[1] += np.random.uniform(-self.args.push_linear, self.args.push_linear)
    self.data.qvel[5] += np.random.uniform(-self.args.push_yaw, self.args.push_yaw)
    print("[TEST] random push applied")

  def handle_key(self, key: int):
    if key in (glfw.KEY_0, glfw.KEY_KP_0):
      self.running = False
    elif key in (glfw.KEY_ENTER, glfw.KEY_KP_ENTER):
      self.reset()
      print("[INFO] reset")
    elif key in (glfw.KEY_8, glfw.KEY_KP_8):
      self.command[:] = [self.args.keyboard_step, 0.0, 0.0]
    elif key in (glfw.KEY_2, glfw.KEY_KP_2):
      self.command[:] = [-self.args.keyboard_step, 0.0, 0.0]
    elif key in (glfw.KEY_4, glfw.KEY_KP_4):
      self.command[:] = [0.0, self.args.keyboard_step, 0.0]
    elif key in (glfw.KEY_6, glfw.KEY_KP_6):
      self.command[:] = [0.0, -self.args.keyboard_step, 0.0]
    elif key in (glfw.KEY_7, glfw.KEY_KP_7):
      self.command[:] = [0.0, 0.0, self.args.keyboard_yaw_step]
    elif key in (glfw.KEY_9, glfw.KEY_KP_9):
      self.command[:] = [0.0, 0.0, -self.args.keyboard_yaw_step]
    elif key in (glfw.KEY_5, glfw.KEY_KP_5):
      self.command[:] = 0.0
    elif key in (glfw.KEY_SLASH, glfw.KEY_KP_DIVIDE):
      self.push()

  def run(self):
    self.running = True
    print("[INFO] Lightweight velocity player")
    print("[KEYS] 8/2/4/6 move, 7/9 yaw, 5 stop, / push, Enter reset, 0 quit")
    if self.args.no_viewer:
      for i in range(self.args.steps):
        if i % self.args.decimation == 0:
          self.apply_action(self.policy(self.build_observation(i // self.args.decimation)))
        mujoco.mj_step(self.model, self.data)
      return
    with mujoco.viewer.launch_passive(
      self.model,
      self.data,
      key_callback=self.handle_key,
      show_left_ui=True,
      show_right_ui=True,
    ) as viewer:
      viewer.cam.type = mujoco.mjtCamera.mjCAMERA_TRACKING
      viewer.cam.trackbodyid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "torso_link")
      viewer.cam.distance = 4.0
      sim_i = 0
      policy_i = 0
      while viewer.is_running() and self.running:
        step_start = time.time()
        if sim_i % self.args.decimation == 0:
          action = self.policy(self.build_observation(policy_i))
          self.apply_action(action)
          policy_i += 1
        mujoco.mj_step(self.model, self.data)
        sim_i += 1
        if sim_i % self.args.render_every == 0:
          viewer.sync()
        sleep_time = self.args.sim_dt - (time.time() - step_start)
        if sleep_time > 0:
          time.sleep(sleep_time)


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--onnx-file", type=Path, default=DEFAULT_ONNX)
  parser.add_argument("--xml-file", type=Path, default=DEFAULT_XML)
  parser.add_argument("--vx", type=float, default=0.0)
  parser.add_argument("--vy", type=float, default=0.0)
  parser.add_argument("--yaw", type=float, default=0.0)
  parser.add_argument("--sim-dt", type=float, default=0.002)
  parser.add_argument("--decimation", type=int, default=10)
  parser.add_argument("--gait-period", type=float, default=0.6)
  parser.add_argument("--keyboard-step", type=float, default=0.35)
  parser.add_argument("--keyboard-yaw-step", type=float, default=0.5)
  parser.add_argument("--push-linear", type=float, default=0.8)
  parser.add_argument("--push-yaw", type=float, default=1.2)
  parser.add_argument("--kp", type=float, default=40.0)
  parser.add_argument("--kd", type=float, default=2.0)
  parser.add_argument("--render-every", type=int, default=1)
  parser.add_argument("--no-viewer", action="store_true")
  parser.add_argument("--steps", type=int, default=200)
  args = parser.parse_args()
  args.control_dt = args.sim_dt * args.decimation
  return args


def main():
  VelocityLitePlayer(parse_args()).run()


if __name__ == "__main__":
  main()
