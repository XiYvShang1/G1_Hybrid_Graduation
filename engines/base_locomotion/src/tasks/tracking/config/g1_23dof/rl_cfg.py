"""G1 23DoF 动作跟踪 / Mimic 任务的 PPO 训练参数。"""

from mjlab.rl import (
  RslRlModelCfg,
  RslRlOnPolicyRunnerCfg,
  RslRlPpoAlgorithmCfg,
)


def unitree_g1_23dof_tracking_ppo_runner_cfg() -> RslRlOnPolicyRunnerCfg:
  """创建动作跟踪 PPO runner 配置。

  动作跟踪的观测维度比速度跟踪更高，因为还包含参考 motion 的目标信息。
  这里仍使用 actor/critic MLP + PPO，只是实验名、保存间隔和总迭代数不同。
  """
  return RslRlOnPolicyRunnerCfg(
    # Actor 根据机器人当前状态和参考动作目标输出 23 个关节动作。
    actor=RslRlModelCfg(
      hidden_dims=(512, 256, 128),
      activation="elu",
      obs_normalization=True,
      distribution_cfg={
        "class_name": "GaussianDistribution",
        "init_std": 1.0,
        "std_type": "scalar",
      },
    ),
    # Critic 用更丰富的状态评估 mimic 策略质量。
    critic=RslRlModelCfg(
      hidden_dims=(512, 256, 128),
      activation="elu",
      obs_normalization=True,
    ),
    # 动作跟踪的 entropy 系数稍小，让策略更专注于贴合参考动作。
    algorithm=RslRlPpoAlgorithmCfg(
      value_loss_coef=1.0,
      use_clipped_value_loss=True,
      clip_param=0.2,
      entropy_coef=0.005,
      num_learning_epochs=5,
      num_mini_batches=4,
      learning_rate=1.0e-3,
      schedule="adaptive",
      gamma=0.99,
      lam=0.95,
      desired_kl=0.01,
      max_grad_norm=1.0,
    ),
    # 训练日志默认写入 logs/rsl_rl/g1_23dof_tracking/...
    experiment_name="g1_23dof_tracking",
    save_interval=500,
    num_steps_per_env=24,
    max_iterations=30001,
  )
