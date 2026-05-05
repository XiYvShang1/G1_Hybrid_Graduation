"""Unitree G1 23DoF 动作跟踪环境配置。

动作跟踪任务的目标是：读取一个参考 motion 文件，让策略输出 23 个关节动作，
使机器人尽量模仿参考动作中的根节点、身体部位、关节位置和速度。
"""

from src.assets.robots.unitree_g1.g1_23dof_constants import (
  G1_23DOF_ACTION_SCALE,
  get_g1_23dof_robot_cfg,
)
from mjlab.envs import ManagerBasedRlEnvCfg
from mjlab.envs.mdp.actions import JointPositionActionCfg
from mjlab.managers.observation_manager import ObservationGroupCfg
from mjlab.sensor import ContactMatch, ContactSensorCfg
from mjlab.tasks.tracking.mdp import MotionCommandCfg

from src.tasks.tracking.tracking_env_cfg import make_tracking_env_cfg


def unitree_g1_23dof_flat_tracking_env_cfg(
  has_state_estimation: bool = True,
  play: bool = False,
) -> ManagerBasedRlEnvCfg:
  """创建 G1 23DoF 平地动作跟踪 / Mimic 配置。

  这个函数是 `Unitree-G1-23Dof-Tracking` 的核心环境配置。它从 mjlab 的通用
  motion tracking 模板出发，替换成 G1 23DoF 机器人，并指定需要跟踪的身体
  部位、终止条件和部署/回放模式下的简化设置。

  Args:
    has_state_estimation: 是否假设策略能拿到状态估计信息。当前项目默认使用 True。
    play: True 表示回放/演示模式，会关闭训练扰动和随机初始状态。
  """
  cfg = make_tracking_env_cfg()

  # 场景实体：动作跟踪训练的主体就是 G1 23DoF 机器人。
  cfg.scene.entities = {"robot": get_g1_23dof_robot_cfg()}

  # 自碰撞传感器用于给 mimic 策略施加安全约束，避免模仿时身体乱撞。
  self_collision_cfg = ContactSensorCfg(
    name="self_collision",
    primary=ContactMatch(mode="subtree", pattern="pelvis", entity="robot"),
    secondary=ContactMatch(mode="subtree", pattern="pelvis", entity="robot"),
    fields=("found", "force"),
    reduce="none",
    num_slots=1,
    history_length=4,
  )
  cfg.scene.sensors = (self_collision_cfg,)

  # 策略动作是 23 个关节的位置目标，缩放表来自机器人执行器参数。
  joint_pos_action = cfg.actions["joint_pos"]
  assert isinstance(joint_pos_action, JointPositionActionCfg)
  joint_pos_action.scale = G1_23DOF_ACTION_SCALE

  # motion command 负责从 npz 参考动作中采样目标姿态，并把目标喂给环境。
  motion_cmd = cfg.commands["motion"]
  assert isinstance(motion_cmd, MotionCommandCfg)
  motion_cmd.anchor_body_name = "torso_link"
  # 这些 body 是 mimic 重点对齐的身体部位：腿、躯干、手臂和末端。
  motion_cmd.body_names = (
    "pelvis",
    "left_hip_roll_link",
    "left_knee_link",
    "left_ankle_roll_link",
    "right_hip_roll_link",
    "right_knee_link",
    "right_ankle_roll_link",
    "torso_link",
    "left_shoulder_roll_link",
    "left_elbow_link",
    "left_wrist_roll_rubber_hand",
    "right_shoulder_roll_link",
    "right_elbow_link",
    "right_wrist_roll_rubber_hand",
  )

  # 随机化脚底摩擦和躯干质量中心，提高策略对物理扰动的适应性。
  cfg.events["foot_friction"].params[
    "asset_cfg"
  ].geom_names = r"^(left|right)_foot[1-7]_collision$"
  cfg.events["base_com"].params["asset_cfg"].body_names = ("torso_link",)

  # 如果脚或手等末端偏离参考动作太多，就提前终止 episode。
  cfg.terminations["ee_body_pos"].params["body_names"] = (
    "left_ankle_roll_link",
    "right_ankle_roll_link",
    "left_wrist_roll_rubber_hand",
    "right_wrist_roll_rubber_hand",
  )

  cfg.viewer.body_name = "torso_link"

  # 如果不使用状态估计，就删掉真实系统中不容易直接获得的观测项。
  if not has_state_estimation:
    new_actor_terms = {
      k: v
      for k, v in cfg.observations["actor"].terms.items()
      if k not in ["motion_anchor_pos_b", "base_lin_vel"]
    }
    cfg.observations["actor"] = ObservationGroupCfg(
      terms=new_actor_terms,
      concatenate_terms=True,
      enable_corruption=True,
    )

  # 回放模式：关闭观测噪声、外部推扰和随机状态初始化，让动作从开头稳定播放。
  if play:
    # Effectively infinite episode length.
    cfg.episode_length_s = int(1e9)

    cfg.observations["actor"].enable_corruption = False
    cfg.events.pop("push_robot", None)

    # Disable RSI randomization.
    motion_cmd.pose_range = {}
    motion_cmd.velocity_range = {}

    motion_cmd.sampling_mode = "start"

  return cfg
