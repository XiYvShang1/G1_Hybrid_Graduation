# 安装说明

## Conda 环境

```bash
conda env create -f environment.yml
conda activate g1-23dof
```

检查入口：

```bash
python -m cli status
python -m cli check-paths
```

## Python 依赖

项目根目录依赖很少，主要用于 CLI 和测试。训练依赖由底层 `engines/base_locomotion` 使用，通常需要：

```text
torch
mujoco
mjlab
onnx
onnxruntime
tensorboard
hydra-core
omegaconf
tyro
```

## WSL 说明

Windows 下的训练和仿真命令会自动包装成 WSL 命令。默认 Python 路径是：

```text
/home/xiyv/miniconda3/envs/unitree_rl_mjlab/bin/python
```

如果你的环境不同，可以显式指定：

```bash
python -m cli train-tracking --python /path/to/python
```

## build-sim 原生依赖

```bash
sudo apt install -y build-essential cmake libeigen3-dev libboost-program-options-dev libyaml-cpp-dev zlib1g-dev
```

部署侧仿真还需要：

```text
unitree_sdk2
cyclonedds
iceoryx
```
