# 基础策略适配层

该适配层用于接入基础运动训练能力，并向主仓输出基础任务与策略相关的登记信息。

## 适配边界

- 输入：基础任务配置、训练入口、部署参数文件。
- 输出：基础任务登记项、策略产物登记项、部署交接记录。
- 当前阶段：优先对接任务入口与参数路径，不迁移外部训练实现。

## 默认入口（可按需替换）

- `scripts/train.py`
- `scripts/play.py`
- `scripts/csv_to_npz.py`
- `src/tasks/velocity/config/g1_23dof/`
- `src/assets/robots/unitree_g1/g1_23dof_constants.py`
- `deploy/robots/g1_23dof/config/policy/velocity/`
