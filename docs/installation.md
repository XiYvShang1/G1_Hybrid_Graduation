# 安装与环境

本项目建议在 Windows + WSL2 环境下运行。顶层 CLI 会在检测到 Linux Python 路径时自动包装 WSL 命令，因此可以在 Windows 侧执行 `python -m cli ...`，训练和仿真实际在 WSL 中运行。

## 推荐环境

- Windows 11 + WSL2
- WSL Ubuntu 22.04
- NVIDIA GPU 与可用 CUDA 驱动
- Conda 或 Mamba
- Python 3.11
- CMake 3.16 或更高版本
- Unitree SDK2 与 CycloneDDS，用于部署侧仿真和控制器

## Conda 环境

在仓库根目录创建环境：

```bash
conda env create -f environment.yml
conda activate g1-23dof
```

如果使用本机已有 WSL 环境，项目默认配置指向：

```text
/home/xiyv/miniconda3/envs/unitree_rl_mjlab/bin/python
```

也可以在命令中显式覆盖：

```bash
python -m cli train-velocity --python /path/to/python
python -m cli train-tracking --python /path/to/python
```

## Python 依赖

项目基础依赖：

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

训练引擎依赖：

```bash
pip install -r requirements-algorithms.txt
```

核心算法和运行时依赖包括：

```text
mjlab
torch
mujoco
tyro
onnx
onnxruntime
scipy
tensorboard
```

## build-sim 原生依赖

`python -m cli build-sim` 会编译两个原生程序：

```text
engines/base_locomotion/simulate/build/unitree_mujoco
engines/base_locomotion/deploy/robots/g1_23dof/build/g1_ctrl
```

WSL 内需要先安装基础编译依赖：

```bash
sudo apt update
sudo apt install -y build-essential cmake git libeigen3-dev libboost-program-options-dev libyaml-cpp-dev zlib1g-dev
```

部署控制器还需要：

```text
unitree_sdk2
cyclonedds
iceoryx
```

ONNX Runtime 库随部署目录放在：

```text
engines/base_locomotion/deploy/thirdparty/
```

如果 `build-sim` 失败，优先检查 `unitree_sdk2`、CycloneDDS 和 Iceoryx 是否安装在 CLI 实际调用的同一个 WSL 环境中。
