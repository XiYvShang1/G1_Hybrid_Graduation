# 仿真说明

本项目保留三类仿真：训练侧策略回放、23DoF 部署闭环仿真、29DoF 已训练策略 MuJoCo 演示。

## 策略回放

回放速度策略：

```bash
python -m cli play-velocity --checkpoint engines/base_locomotion/logs/rsl_rl/.../model_1000.pt
```

回放动作跟踪策略：

```bash
python -m cli play-tracking --checkpoint engines/base_locomotion/logs/rsl_rl/.../model_1000.pt
```

回放 ONNX 策略：

```bash
python -m cli play-onnx --onnx-file engines/base_locomotion/logs/rsl_rl/.../policy.onnx
```

## 23DoF 部署侧仿真

先编译仿真器和控制器：

```bash
python -m cli build-23dof-sim
```

启动完整本地仿真栈：

```bash
python -m cli sim-23dof-stack --network lo
```

也可以分两个终端启动：

```bash
python -m cli sim-23dof
python -m cli deploy-23dof-sim --network lo
```

## 29DoF 已训练策略仿真

```bash
python -m cli sim-29dof-mujoco
python -m cli sim-29dof-mujoco --xml-path g1_description/g1_29dof_LieDown.xml
```

这条线使用 `deployments/g1_29dof` 中已有的 29DoF 策略和 FSM，不参与 23DoF 训练。

## build-23dof-sim 前置依赖

`build-23dof-sim` 需要 WSL 原生依赖：

```bash
sudo apt install -y build-essential cmake libeigen3-dev libboost-program-options-dev libyaml-cpp-dev zlib1g-dev
```

还需要 Unitree 通信依赖：

```text
unitree_sdk2
cyclonedds
iceoryx
```

先 dry-run 检查命令：

```bash
python -m cli build-23dof-sim --dry-run
python -m cli sim-23dof-stack --dry-run
python -m cli sim-29dof-mujoco --dry-run
```
