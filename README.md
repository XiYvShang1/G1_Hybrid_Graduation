# G1 23DoF 强化学习训练与仿真

本项目面向 Unitree G1 23DoF，保留两条核心路线：

- `Unitree-G1-23Dof-Flat`：速度跟踪训练，用于基础行走能力。
- `Unitree-G1-23Dof-Tracking`：动作跟踪 / Mimic 训练，用于模仿参考动作。

项目现在只围绕 G1 23DoF 展开，不再保留额外的注册表、契约层和多机器人示例。日常使用只需要根目录的 `cli.py`、`configs/g1_23dof.yaml`、`engines/base_locomotion` 和 `docs/`。

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

准备默认动作文件：

```bash
python -m cli prepare-motion
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
python -m cli build-sim
python -m cli sim-stack --network lo
```

任何训练或仿真命令都可以先加 `--dry-run` 查看真实生成的命令：

```bash
python -m cli train-tracking --dry-run
python -m cli sim-stack --dry-run
```

## 目录结构

```text
configs/                  G1 23DoF 默认项目配置。
docs/                     安装、训练、仿真、部署和架构说明。
engines/base_locomotion/  训练任务、动作资产、MuJoCo 回放和 G1 23DoF 控制器。
runtime/                  本地生成的动作文件和临时输出。
tests/                    CLI 冒烟测试。
cli.py                    项目统一命令入口。
environment.yml           Conda 环境文件。
```

## 核心命令

```bash
python -m cli prepare-motion
python -m cli train-velocity
python -m cli train-tracking
python -m cli play-velocity --checkpoint <model.pt>
python -m cli play-tracking --checkpoint <model.pt>
python -m cli play-onnx --onnx-file <policy.onnx>
python -m cli build-sim
python -m cli sim-stack --network lo
```

## 文档

- [安装说明](docs/installation.md)
- [训练说明](docs/training.md)
- [仿真说明](docs/simulation.md)
- [部署说明](docs/deployment.md)
- [架构说明](docs/architecture.md)

## 验证

```bash
python -m unittest tests.test_cli_smoke
```

冒烟测试只检查命令入口和路径，不会启动长时间训练、编译或真实仿真。真实运行仍依赖本机 WSL、GPU、MuJoCo、Unitree SDK2 和 CycloneDDS 环境。
