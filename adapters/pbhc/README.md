# 技能策略适配层

该适配层用于接入技能动作训练与部署检查能力，并向主仓输出技能任务与策略登记信息。

## 适配边界

- 输入：动作资产、技能训练配置、策略导出配置。
- 输出：技能任务登记项、技能策略登记项、部署 handoff 记录。
- 当前阶段：优先登记可调用入口与产物位置，不修改外部训练内核。

## 默认入口（可按需替换）

- `smpl_retarget/mink_retarget/convert_fit_motion.py`
- `humanoidverse/train_agent.py`
- `humanoidverse/utils/motion_lib/`
- `humanoidverse/urci.py`
- `DemoTest/new_mjlab_real/`
