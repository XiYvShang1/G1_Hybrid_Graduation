# 部署说明

当前项目保留两层部署：

- 23DoF：本项目训练出来的速度跟踪 / 动作跟踪策略部署。
- 29DoF：已有训练好策略的 MuJoCo / 真机部署演示。

## 23DoF 部署

```text
engines/base_locomotion/deploy/robots/g1_23dof
```

策略文件默认放在：

```text
engines/base_locomotion/deploy/robots/g1_23dof/config/policy/velocity/v0/exported/policy.onnx
engines/base_locomotion/deploy/robots/g1_23dof/config/policy/mimic/dance1_subject2/exported/policy.onnx
```

对应部署参数：

```text
engines/base_locomotion/deploy/robots/g1_23dof/config/policy/velocity/v0/params/deploy.yaml
engines/base_locomotion/deploy/robots/g1_23dof/config/policy/mimic/dance1_subject2/params/deploy.yaml
```

## 本地仿真

```bash
python -m cli build-23dof-sim
python -m cli sim-23dof-stack --network lo
```

`sim-23dof-stack` 会先启动 MuJoCo 仿真器，再启动 G1 23DoF 控制器。控制器退出后，仿真器也会被关闭。

## 29DoF 部署演示

29DoF 部署层位于：

```text
deployments/g1_29dof
```

它加载已有训练好的 29DoF 权重，用 FSM 完成行走、站立、阻尼保护和动作技能切换。

MuJoCo 演示：

```bash
python -m cli sim-29dof-mujoco
python -m cli sim-29dof-mujoco --xml-path g1_description/g1_29dof_LieDown.xml
```

真机入口只建议先 dry-run：

```bash
python -m cli deploy-29dof-real --dry-run
```

## 实机提醒

实机部署前需要重新确认：

- ONNX 策略输入输出维度。
- `deploy.yaml` 里的观测顺序、动作缩放、默认关节角、刚度和阻尼。
- 网络接口和 Unitree SDK2 / CycloneDDS 配置。
- 低速、悬空、保护绳等安全测试流程。
