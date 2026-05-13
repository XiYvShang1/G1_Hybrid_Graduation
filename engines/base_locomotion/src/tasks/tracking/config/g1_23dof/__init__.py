"""把 G1 23DoF 动作跟踪任务注册进 mjlab 任务表。

底层 scripts/train.py 根据任务名加载配置。这里把
`Unitree-G1-23Dof-Tracking` 绑定到 G1 23DoF mimic 环境和动作跟踪 runner。
"""

from mjlab.tasks.registry import register_mjlab_task
from src.tasks.tracking.rl import MotionTrackingOnPolicyRunner

from .env_cfgs import unitree_g1_23dof_flat_tracking_env_cfg
from .rl_cfg import unitree_g1_23dof_tracking_ppo_runner_cfg

# 这是根目录 `python -m cli train-tracking` 最终会调用的任务名。
register_mjlab_task(
  task_id="Unitree-G1-23Dof-Tracking",
  env_cfg=unitree_g1_23dof_flat_tracking_env_cfg(),
  play_env_cfg=unitree_g1_23dof_flat_tracking_env_cfg(play=True),
  rl_cfg=unitree_g1_23dof_tracking_ppo_runner_cfg(),
  runner_cls=MotionTrackingOnPolicyRunner,
)

# 预训练 mimic ONNX 使用的是不含状态估计项的 124 维 actor 观测。
# 保留默认 130 维任务用于后续重新训练，同时单独注册一个回放/部署兼容任务。
register_mjlab_task(
  task_id="Unitree-G1-23Dof-Tracking-No-State-Estimation",
  env_cfg=unitree_g1_23dof_flat_tracking_env_cfg(has_state_estimation=False),
  play_env_cfg=unitree_g1_23dof_flat_tracking_env_cfg(
    has_state_estimation=False,
    play=True,
  ),
  rl_cfg=unitree_g1_23dof_tracking_ppo_runner_cfg(),
  runner_cls=MotionTrackingOnPolicyRunner,
)
