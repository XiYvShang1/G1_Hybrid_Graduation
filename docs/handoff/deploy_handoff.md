# 训练到部署交接清单

本文件定义项目在接收任何训练产物时必须补齐的部署语义。没有完成以下交接的策略，不视为具备部署或仿真验证条件。

## 1. obs

必须说明：

- observation 维度
- 拼接顺序
- 每一项来源
- 是否包含历史帧
- 是否包含 command / phase / reference motion
- 与训练配置或 deploy yaml 的对应文件

## 2. action

必须说明：

- action 维度
- action 顺序
- action 是 residual 还是 absolute target
- action scale / offset 来源
- 输出是否经过 clip
- 与机器人关节顺序的对应关系

## 3. default

必须说明：

- default pose 来源
- default pose 维度和关节顺序
- 是否与 deploy yaml / robot constants 一致

## 4. scale

必须说明：

- action scale 来源
- observation scale 来源
- clip 范围
- 与训练配置的一致性检查方式

## 5. hybrid command

必须说明策略输出最终如何变成电机五参数：

```text
q_des
dq_des
k_p
k_d
```

当前默认安全主线是位置模式：

```text
q_des != 0
k_p > 0
k_d > 0
```

## 6. damping fallback

必须说明：

- 何时触发阻尼态
- 阻尼态五参数具体值
- 哪个文件负责生成阻尼命令
- 过限、姿态异常、通信异常时是否强制回退

## 7. 第一阶段验证方式

第一阶段只要求完成离线 handoff 检查：

- registry 中存在策略产物记录
- deploy contract 中存在 obs/action/default/scale 信息
- 策略文件路径和配置文件路径可追踪
- 未声明完整 handoff 的策略不得标记为 deploy-ready
