# 系统架构说明

## 总体目标

本项目围绕 Unitree G1 构建一条混合式动作策略系统链：

```text
动作源数据
  -> 动作重定向 / 动作资产生成
  -> 基础运动训练与技能动作训练
  -> 策略产物注册
  -> 部署语义恢复与验证
```

## 三仓职责边界

### GVHMR2PBHC：动作资产前端

该仓库负责从 GVHMR 或 SMPL 相关输出中整理出 PBHC 可继续 retarget 和训练的动作资产。它适合作为本项目的上游动作数据入口，而不是训练主仓。

关键语义：

- `.pt -> .npz`
- `.npz -> PBHC retarget .pkl`
- motion pkl 清洗、冻结、插值
- 动作资产合法性检查

### unitree_rl_mjlab：基础能力训练线

该仓库更适合作为 G1 23DoF 基础 locomotion / velocity policy 的来源。它提供 MuJoCo 训练、回放和 sim2real 风格 deploy 参数模板。

关键语义：

- `Unitree-G1-23Dof-Flat / Rough`
- velocity command tracking
- tracking `.npz` motion reference
- deploy.yaml 中的 obs layout、action scale、default pose、kp/kd

### PBHC：动作技能与部署语义主线

PBHC 覆盖动作源、重定向、motion tracking 训练、策略导出、MuJoCo/URCI 验证与实机 handoff，是本混合项目的技能动作主线。

关键语义：

- SMPL / AMASS / robot motion pkl
- motion tracking 训练
- ONNX / JIT 策略产物
- deploy handoff
- lowstate -> obs -> action -> hybrid command

## 推荐集成方式

本项目采用壳工程方式：

1. **合同层**记录动作资产、关节顺序、策略产物和部署 handoff。
2. **适配层**封装旧仓库入口，不复制训练内核。
3. **注册表**保存本项目能识别和展示的 motion、task、policy。
4. **pipeline 层**串联流程，并在后续阶段补充真实命令调用。

## 为什么不直接合并训练框架

三个仓库之间存在真实工程缝：

- PBHC 常用 `.pkl` 动作资产，mjlab tracking 更自然使用 `.npz`。
- PBHC 和 mjlab 的 obs/action/deploy 配置语义不完全一致。
- 训练环境、仿真框架、导出路径和依赖链不同。

因此第一阶段只抽取合同层，不抽取训练层。
