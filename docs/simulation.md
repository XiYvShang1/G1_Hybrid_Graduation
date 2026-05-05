# 仿真说明

本项目保留两类仿真：训练侧策略回放，以及部署侧 MuJoCo + G1 23DoF 控制器仿真。

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

## 部署侧仿真

先编译仿真器和控制器：

```bash
python -m cli build-sim
```

启动完整本地仿真栈：

```bash
python -m cli sim-stack --network lo
```

也可以分两个终端启动：

```bash
python -m cli sim
python -m cli deploy-sim --network lo
```

## build-sim 前置依赖

`build-sim` 需要 WSL 原生依赖：

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
python -m cli build-sim --dry-run
python -m cli sim-stack --dry-run
```
