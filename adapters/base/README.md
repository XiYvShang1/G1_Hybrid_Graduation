# 基础策略适配层

该适配层用于接入项目内基础运动训练能力，并输出基础任务与策略相关的登记信息。

## 适配边界

- 输入：基础任务配置、训练入口、部署参数文件。
- 输出：基础任务登记项、策略产物登记项、部署交接记录。
- 当前阶段：优先对接任务入口与参数路径。

## 默认入口

- `pipelines/train_base_policy.py`
- `pipelines/export_policy_bundle.py`
- `configs/deploy/example_deploy_handoff.yaml`
