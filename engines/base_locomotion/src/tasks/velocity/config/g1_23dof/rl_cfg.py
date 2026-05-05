"""G1 23DoF 速度跟踪任务的 PPO 训练参数。"""

from mjlab.rl import (
  RslRlModelCfg,
  RslRlOnPolicyRunnerCfg,
  RslRlPpoAlgorithmCfg,
)


def unitree_g1_23dof_ppo_runner_cfg() -> RslRlOnPolicyRunnerCfg:
  """创建速度跟踪 PPO runner 配置。

  这里主要定义 actor/critic 网络结构、PPO 超参数、日志目录名、保存间隔和
  训练总迭代数。环境本身的奖励/观测在 env_cfgs.py 中定义。
  """
  return RslRlOnPolicyRunnerCfg(
    # Actor 输入观测，输出 23 个关节动作；这里使用三层 MLP。
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
    # Critic 用更完整的 critic 观测估计 value。
    critic=RslRlModelCfg(
      hidden_dims=(512, 256, 128),
      activation="elu",
      obs_normalization=True,
    ),
    # PPO 核心超参数：clip、entropy、GAE、学习率调度等。
    algorithm=RslRlPpoAlgorithmCfg(
      value_loss_coef=1.0,
      use_clipped_value_loss=True,
      clip_param=0.2,
      entropy_coef=0.01,
      num_learning_epochs=5,
      num_mini_batches=4,
      learning_rate=1.0e-3,
      schedule="adaptive",
      gamma=0.99,
      lam=0.95,
      desired_kl=0.01,
      max_grad_norm=1.0,
    ),
    # 训练日志默认写入 logs/rsl_rl/g1_23dof_velocity/...
    experiment_name="g1_23dof_velocity",
    save_interval=100,
    num_steps_per_env=24,
    max_iterations=10001,
  )
