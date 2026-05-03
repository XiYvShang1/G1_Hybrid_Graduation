# 部署说明

部署被拆成明确的交接流程。策略训练完成不等于策略已经可以直接上实机。

## 策略产物位置

速度策略模板：

```text
engines/base_locomotion/deploy/robots/g1_23dof/config/policy/velocity/v0/exported/policy.onnx
engines/base_locomotion/deploy/robots/g1_23dof/config/policy/velocity/v0/params/deploy.yaml
```

动作跟踪策略模板：

```text
engines/base_locomotion/deploy/robots/g1_23dof/config/policy/mimic/dance1_subject2/exported/policy.onnx
engines/base_locomotion/deploy/robots/g1_23dof/config/policy/mimic/dance1_subject2/params/deploy.yaml
```

这些策略产物会登记在项目注册表中：

```bash
python -m cli status
python -m cli check-paths
```

## 本地仿真部署

先构建：

```bash
python -m cli build-sim
```

启动本地部署侧仿真：

```bash
python -m cli sim-stack --network lo
```

等价的双终端流程：

```bash
python -m cli sim
python -m cli deploy-sim --network lo
```

## 实机部署注意事项

实机部署前必须先完成本地仿真验证，并确保机器人处于安全支撑状态。

检查项：

- 机器人在控制器启动前已经安全支撑。
- 机器人进入预期的调试 / 阻尼模式。
- 主机网口已经配置到 Unitree 控制网络。
- `deploy.yaml` 与策略的 action scale、default pose、stiffness、damping、joint map、observation layout 一致。
- 导出的策略来自同一个 G1 23DoF 任务和同一个关节语义契约。

实机控制器命令形态：

```bash
python -m cli deploy-sim --network <robot_network_interface>
```

例如：

```bash
python -m cli deploy-sim --network enp5s0
```

## 交接检查

部署交接元数据检查入口：

```bash
python -m cli workflow --config configs/workflows/example_orchestration.yaml --execute --stages skill
```

这个检查确认必要交接字段是否存在。它本身不证明实机安全，只是进入仿真和实机测试前的一道工程门槛。
