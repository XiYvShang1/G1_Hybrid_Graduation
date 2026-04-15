# PBHC 适配层

该适配层负责把 `PBHC/` 中的动作重定向、动作跟踪训练和部署语义恢复能力接入本毕设主仓。

## 适配边界

- 输入：SMPL / robot motion `.pkl`、PBHC 训练配置、导出策略。
- 输出：技能动作策略注册项和部署 handoff 记录。
- 第一阶段不改 PBHC 内部训练框架，只记录可调用入口和产物位置。

## 重点旧仓库入口

- `PBHC/smpl_retarget/mink_retarget/convert_fit_motion.py`
- `PBHC/humanoidverse/train_agent.py`
- `PBHC/humanoidverse/utils/motion_lib/`
- `PBHC/humanoidverse/urci.py`
- `PBHC/DemoTest/new_mjlab_real/`
