# G1 23DoF 强化学习训练与仿真

本项目面向 Unitree G1，主线是 23DoF 强化学习训练，同时保留 29DoF 已训练策略部署演示：

- `Unitree-G1-23Dof-Flat`：速度跟踪训练，用于基础行走能力。
- `Unitree-G1-23Dof-Tracking`：动作跟踪 / Mimic 训练，用于模仿参考动作。
- `motion_pipeline/`：项目内置视频动作流水线，把 MP4 转成 Mimic 训练需要的 G1 动作 npz。
- 29DoF 部署：加载已有策略，用于 MuJoCo / 真机部署演示。

项目不再保留额外的注册表、契约层和多机器人示例。日常使用主要看根目录 `cli.py`、`configs/g1_23dof.yaml`、`motion_pipeline`、`engines/base_locomotion`、`deployments/g1_29dof` 和 `docs/`。

![G1 23DoF 动作跟踪效果](docs/assets/g1_23dof_motion_demo.png)

## 快速开始

创建 Conda 环境：

```bash
conda env create -f environment.yml
conda activate g1-23dof
```

检查项目路径：

```bash
python -m cli status
python -m cli check-paths
```

如需使用分离的 Conda 环境，可以通过环境变量指定各模块 Python。模板见 `configs/runtime.example.env`：

```bash
export G1_MJLAB_PYTHON=python
export G1_GVHMR_PYTHON=python
export G1_RETARGET_PYTHON=python
export G1_29DOF_PYTHON=python
```

准备默认动作文件：

```bash
python -m cli prepare-motion
```

一条命令查看完整视频动作链路：

```bash
python -m cli motion-pipeline path/to/input.mp4 --name demo --person 0 --dry-run
```

真实运行时，这条命令会按固定目录生成：

```text
runtime/motion_pipeline/demo/source_motion/demo.npz
runtime/motion_pipeline/demo/demo_g1.csv
runtime/motion_pipeline/demo/demo_g1.npz
```

如果想分步调试，也可以拆开执行：

```bash
python -m cli video-to-smpl path/to/input.mp4 --person 0 --output runtime/example_motion/example_smpl.npz
python -m cli retarget-motion path/to/smpl_motion_folder
python -m cli pkl-to-csv path/to/retarget.pkl --output runtime/example_motion/example_motion.csv
python -m cli csv-to-npz runtime/example_motion/example_motion.csv --output runtime/example_motion/example_motion.npz
```

训练速度跟踪策略：

```bash
python -m cli train-velocity
```

训练动作跟踪策略：

```bash
python -m cli train-tracking
```

回放训练好的 checkpoint：

```bash
python -m cli play-velocity --checkpoint engines/base_locomotion/logs/rsl_rl/.../model_1000.pt
python -m cli play-tracking --checkpoint engines/base_locomotion/logs/rsl_rl/.../model_1000.pt
```

构建并启动部署侧仿真：

```bash
python -m cli build-23dof-sim
python -m cli sim-23dof-stack --network lo
```

运行 29DoF 已训练策略 MuJoCo 演示：

```bash
python -m cli sim-29dof-mujoco
python -m cli sim-29dof-mujoco --xml-path g1_description/g1_29dof_LieDown.xml
```

任何训练或仿真命令都可以先加 `--dry-run` 查看真实生成的命令：

```bash
python -m cli train-tracking --dry-run
python -m cli sim-23dof-stack --dry-run
python -m cli sim-29dof-mujoco --dry-run
```

## 目录结构

```text
configs/                  G1 23DoF 默认项目配置。
docs/                     安装、训练、仿真、部署和架构说明。
motion_pipeline/          视频动作采集、SMPL 转换、G1 重定向和 CSV/NPZ 数据生成。
engines/base_locomotion/  23DoF 训练、回放、仿真和控制器。
deployments/g1_29dof/     29DoF 已训练策略部署演示。
runtime/                  本地生成的动作文件和临时输出。
tests/                    CLI 冒烟测试。
cli.py                    项目统一命令入口。
environment.yml           Conda 环境文件。
```

## 核心命令

```bash
python -m cli prepare-motion
python -m cli motion-pipeline <input.mp4> --name <case>
python -m cli video-to-smpl <input.mp4> --output <smpl.npz>
python -m cli retarget-motion <smpl_motion_folder>
python -m cli pkl-to-csv <retarget.pkl> --output <motion.csv>
python -m cli csv-to-npz <motion.csv> --output <motion.npz>
python -m cli train-velocity
python -m cli train-tracking
python -m cli play-velocity --checkpoint <model.pt>
python -m cli play-tracking --checkpoint <model.pt>
python -m cli play-onnx --onnx-file <policy.onnx>
python -m cli build-23dof-sim
python -m cli sim-23dof-stack --network lo
python -m cli sim-29dof-mujoco
```

## 文档

- [安装说明](docs/installation.md)
- [训练说明](docs/training.md)
- [仿真说明](docs/simulation.md)
- [部署说明](docs/deployment.md)
- [架构说明](docs/architecture.md)
- [第三方组件说明](docs/third_party.md)

## 验证

```bash
python -m unittest tests.test_cli_smoke
```

冒烟测试只检查命令入口和路径，不会启动长时间训练、编译或真实仿真。真实运行仍依赖本机 WSL、GPU、MuJoCo、Unitree SDK2 和 CycloneDDS 环境。
