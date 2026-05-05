# 部署说明

当前项目只保留 G1 23DoF 部署侧仿真控制器：

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
python -m cli build-sim
python -m cli sim-stack --network lo
```

`sim-stack` 会先启动 MuJoCo 仿真器，再启动 G1 23DoF 控制器。控制器退出后，仿真器也会被关闭。

## 实机提醒

实机部署前需要重新确认：

- ONNX 策略输入输出维度。
- `deploy.yaml` 里的观测顺序、动作缩放、默认关节角、刚度和阻尼。
- 网络接口和 Unitree SDK2 / CycloneDDS 配置。
- 低速、悬空、保护绳等安全测试流程。
