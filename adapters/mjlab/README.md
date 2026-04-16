# unitree_rl_mjlab 适配层

该适配层负责把 `unitree_rl_mjlab/` 的 G1 23DoF 基础训练和部署参数纳入本毕设主仓。

## 适配边界

- 输入：mjlab task id、训练配置、motion `.npz`、deploy.yaml。
- 输出：基础 locomotion 策略注册项和部署 handoff 记录。
- 第一阶段优先登记 velocity policy，不强行迁移 mjlab 训练代码。

## 重点旧仓库入口

- `unitree_rl_mjlab/scripts/train.py`
- `unitree_rl_mjlab/scripts/play.py`
- `unitree_rl_mjlab/scripts/csv_to_npz.py`
- `unitree_rl_mjlab/src/tasks/velocity/config/g1_23dof/`
- `unitree_rl_mjlab/src/assets/robots/unitree_g1/g1_23dof_constants.py`
- `unitree_rl_mjlab/deploy/robots/g1_23dof/config/policy/velocity/`
