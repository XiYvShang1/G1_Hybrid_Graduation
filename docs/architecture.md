# 架构说明

瘦身后，项目只保留 G1 23DoF 主线，不再维护 registry、contracts、adapters、pipelines 等额外包装层。

## 分层

```text
cli.py
  用户入口，负责训练、回放、仿真和路径检查。

configs/g1_23dof.yaml
  项目默认任务、动作文件和仿真目录说明。

engines/base_locomotion/
  核心训练与仿真代码。

runtime/
  本地生成文件，例如 prepare-motion 复制出的动作文件。

docs/
  中文说明文档。
```

## 核心闭环

```text
默认动作 npz
  -> prepare-motion
  -> train-velocity / train-tracking
  -> play-velocity / play-tracking / play-onnx
  -> build-sim / sim-stack
```

## 保留边界

项目只默认支持：

```text
Unitree-G1-23Dof-Flat
Unitree-G1-23Dof-Tracking
engines/base_locomotion/deploy/robots/g1_23dof
```

如果底层训练引擎内部仍有历史 task 变体，它们属于调试能力，不作为本项目主流程讲解。
