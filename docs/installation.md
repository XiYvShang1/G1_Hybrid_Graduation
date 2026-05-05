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

## 运行环境变量

项目代码不绑定任何个人机器路径。默认情况下，CLI 会使用当前激活环境中的 `python`。如果训练、视频恢复、动作重定向和 29DoF 部署分别安装在不同 Conda 环境，可以通过环境变量指定：

```bash
export G1_MJLAB_PYTHON=python
export G1_GVHMR_PYTHON=python
export G1_RETARGET_PYTHON=python
export G1_29DOF_PYTHON=python
```

环境变量模板位于：

```text
configs/runtime.example.env
```

也可以在单次命令中覆盖：

```bash
python -m cli train-tracking --python /path/to/python
python -m cli motion-pipeline input.mp4 --gvhmr-python /path/to/gvhmr/python --retarget-python /path/to/retarget/python --mjlab-python /path/to/mjlab/python
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

## Windows / WSL 说明

项目推荐在 Linux 或 WSL 中运行训练、视频恢复和部署侧仿真。Windows 下如果传入的是 Linux 绝对路径，例如 `/usr/bin/python` 或 Conda 环境中的 `/home/.../bin/python`，CLI 会自动包装成 `wsl.exe bash -lc`。

如果你直接使用当前 Windows Python，只适合跑 CLI 冒烟测试和轻量转换，不建议启动 GPU 训练或 MuJoCo 部署仿真。

```bash
python -m cli train-tracking --dry-run
python -m cli motion-pipeline input.mp4 --dry-run
```

## build-23dof-sim 原生依赖

```bash
sudo apt install -y build-essential cmake libeigen3-dev libboost-program-options-dev libyaml-cpp-dev zlib1g-dev
```

部署侧仿真还需要：

```text
unitree_sdk2
cyclonedds
iceoryx
```

## 视频动作流水线依赖

视频到 SMPL 的源码已经集成在项目内 `motion_pipeline/backends/gvhmr`，本地输入、输出和 checkpoints 不提交。GVHMR 环境建议单独安装：

```bash
cd motion_pipeline/backends/gvhmr
conda create -y -n gvhmr python=3.10
conda activate gvhmr
pip install -r requirements.txt
pip install -e .
```

视频恢复模型需要把权重和人体模型放在本地 `motion_pipeline/backends/gvhmr/inputs/checkpoints/`，该目录已忽略提交。

SMPL 到 G1 的动作重定向代码位于 `motion_pipeline/backends/g1_retarget`。如果要运行 `motion-pipeline`、`retarget-motion` 或 `filter-smpl-motion`，还需要安装额外依赖：

```bash
python -m cli install-retarget-poselib
pip install smplx
pip install git+https://github.com/ZhengyiLuo/SMPLSim.git@master
```

SMPL 官方模型参数不要提交到仓库，放在本地目录：

```text
motion_pipeline/backends/g1_retarget/smpl_retarget/smpl_model/smpl/
```

常用检查命令：

```bash
python -m cli motion-pipeline path/to/input.mp4 --name demo --person 0 --dry-run
python -m cli video-to-smpl path/to/input.mp4 --person 0 --dry-run
python -m cli retarget-motion path/to/smpl_motion_folder --dry-run
python -m cli filter-smpl-motion path/to/smpl_motion_folder --dry-run
```
