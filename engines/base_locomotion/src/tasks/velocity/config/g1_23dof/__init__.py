"""把 G1 23DoF 速度跟踪任务注册进 mjlab 任务表。

底层 scripts/train.py 启动时会 import src.tasks，进而加载这个文件。
register_mjlab_task 会把任务名 `Unitree-G1-23Dof-Flat` 和对应环境配置、
回放配置、PPO 配置、runner 类绑定起来。
"""

from mjlab.tasks.registry import register_mjlab_task
from src.tasks.velocity.rl import VelocityOnPolicyRunner

from .env_cfgs import (
  unitree_g1_23dof_flat_env_cfg,
)
from .rl_cfg import unitree_g1_23dof_ppo_runner_cfg

# 这是根目录 `python -m cli train-velocity` 最终会调用的任务名。
register_mjlab_task(
  task_id="Unitree-G1-23Dof-Flat",
  env_cfg=unitree_g1_23dof_flat_env_cfg(),
  play_env_cfg=unitree_g1_23dof_flat_env_cfg(play=True),
  rl_cfg=unitree_g1_23dof_ppo_runner_cfg(),
  runner_cls=VelocityOnPolicyRunner,
)
