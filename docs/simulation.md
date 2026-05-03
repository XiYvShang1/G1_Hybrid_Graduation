# 仿真说明

本项目有两类仿真路径：

- Python 训练引擎内的 MuJoCo 策略回放。
- 部署侧 `unitree_mujoco` + G1 23DoF 控制器仿真。

## 策略回放

回放速度策略 checkpoint：

```bash
python -m cli play-velocity --checkpoint engines/base_locomotion/logs/rsl_rl/.../model_1000.pt
```

回放动作跟踪策略 checkpoint：

```bash
python -m cli play-tracking --motion-file runtime/example_motion/example_motion.npz --checkpoint engines/base_locomotion/logs/rsl_rl/.../model_1000.pt
```

回放导出的 ONNX 策略：

```bash
python -m cli play-onnx --onnx-file engines/base_locomotion/logs/rsl_rl/.../policy.onnx
```

查看命令但不执行：

```bash
python -m cli play-tracking --checkpoint dummy.pt --dry-run
```

## 部署侧仿真

先编译仿真器和控制器：

```bash
python -m cli build-sim
```

编译产物：

```text
engines/base_locomotion/simulate/build/unitree_mujoco
engines/base_locomotion/deploy/robots/g1_23dof/build/g1_ctrl
```

启动仿真器：

```bash
python -m cli sim
```

另一个终端启动本地仿真控制器：

```bash
python -m cli deploy-sim --network lo
```

也可以用一条命令同时启动：

```bash
python -m cli sim-stack --network lo
```

`sim-stack` 会先启动 `unitree_mujoco`，等待一小段时间，再启动 `g1_ctrl`。控制器退出后，仿真器进程会被关闭。

## build-sim 前置依赖

`build-sim` 需要 WSL 原生依赖，不只是 Python 包：

```bash
sudo apt install -y build-essential cmake libeigen3-dev libboost-program-options-dev libyaml-cpp-dev zlib1g-dev
```

还需要 Unitree 通信依赖：

```text
unitree_sdk2
cyclonedds
iceoryx
```

控制器会链接这里的 ONNX Runtime：

```text
engines/base_locomotion/deploy/thirdparty/onnxruntime-linux-x64-1.22.0
engines/base_locomotion/deploy/thirdparty/onnxruntime-linux-aarch64-1.22.0
```

## 常用检查

先 dry-run 检查命令：

```bash
python -m cli build-sim --dry-run
python -m cli sim-stack --dry-run
```

构建后确认二进制存在：

```text
engines/base_locomotion/simulate/build/unitree_mujoco
engines/base_locomotion/deploy/robots/g1_23dof/build/g1_ctrl
```
