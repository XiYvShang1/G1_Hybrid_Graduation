# 工程架构

这个仓库是围绕 G1 23DoF 构建的项目外壳，内部集成训练和仿真引擎，外部提供统一 CLI、配置、注册表和交接文档。

## 分层

```text
configs/
  面向用户的示例配置：动作资产、workflow、训练任务、策略产物、部署交接。

registry/
  项目资产清单：动作资产、训练任务、策略产物。

contracts/
  动作资产、策略产物、关节契约、部署交接的数据结构。

adapters/
  把项目概念转换成训练引擎命令的薄适配层。

pipelines/
  项目级脚本：动作资产准备、部署交接检查等。

engines/base_locomotion/
  G1 23DoF 训练、回放、部署控制器和仿真代码。

runtime/
  生成的动作资产、workflow 报告和本地日志。
```

## 默认 G1 23DoF 闭环

```text
configs/assets/example_motion_asset.yaml
  -> runtime/example_motion/example_motion.npz
  -> Unitree-G1-23Dof-Flat
  -> Unitree-G1-23Dof-Tracking
  -> registry/policy_registry.yaml
  -> play / play_onnx / sim-stack
```

## 命令归属

项目根目录 CLI 负责日常使用：

```text
python -m cli train-velocity
python -m cli train-tracking
python -m cli play-velocity
python -m cli play-tracking
python -m cli build-sim
python -m cli sim-stack
```

底层训练引擎脚本保留给调试：

```text
engines/base_locomotion/scripts/train.py
engines/base_locomotion/scripts/play.py
engines/base_locomotion/scripts/play_onnx.py
```

## 工程边界

项目默认只服务 G1 23DoF。引擎目录里可能存在其他机器人或任务变体，它们属于底层引擎能力，不作为本项目默认工作流的一部分。

项目公开工作流、注册表示例、文档和 CLI 都围绕以下目标组织：

```text
Unitree-G1-23Dof-Flat
Unitree-G1-23Dof-Tracking
deploy/robots/g1_23dof
```

## 生成文件

这些生成文件不应进入版本控制：

```text
runtime/example_motion/
runtime/orchestration/
engines/base_locomotion/logs/
engines/base_locomotion/wandb/
engines/base_locomotion/simulate/build/
engines/base_locomotion/deploy/robots/*/build/
```
