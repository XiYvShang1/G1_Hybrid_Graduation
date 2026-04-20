# 技能策略适配层

该适配层用于接入项目内技能动作训练与部署检查能力，并输出技能任务与策略登记信息。

## 适配边界

- 输入：动作资产、技能训练配置、策略导出配置。
- 输出：技能任务登记项、技能策略登记项、部署 handoff 记录。
- 当前阶段：优先登记可调用入口与产物位置。

## 默认入口

- `pipelines/train_skill_policy.py`
- `pipelines/export_policy_bundle.py`
- `pipelines/validate_deploy_handoff.py`
