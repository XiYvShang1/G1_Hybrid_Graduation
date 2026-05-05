# 架构说明

瘦身后，项目不再维护 registry、contracts、adapters、pipelines 等额外包装层。现在保留一个清晰的“双层部署”结构：23DoF 是训练主线，29DoF 是已有策略部署演示层。

## 分层

```text
cli.py
  用户入口，负责视频动作流水线、训练、回放、仿真和路径检查。

configs/g1_23dof.yaml
  项目默认任务、动作文件和仿真目录说明。

motion_pipeline/
  项目内置动作数据层，负责 MP4 -> SMPL -> G1 retarget -> CSV -> NPZ。

engines/base_locomotion/
  23DoF 核心训练、回放、MuJoCo 仿真和 C++ 控制器代码。

deployments/g1_29dof/
  29DoF 已训练策略部署演示，包含 FSM、MuJoCo 入口、真机入口和策略权重。

runtime/
  本地生成文件，例如 prepare-motion 复制出的动作文件。

docs/
  中文说明文档。
```

## 核心闭环

```text
默认动作 npz
  -> prepare-motion
  或 mp4 -> motion-pipeline
  或 mp4 -> video-to-smpl -> retarget-motion -> pkl-to-csv -> csv-to-npz
  -> train-velocity / train-tracking
  -> play-velocity / play-tracking / play-onnx
  -> build-23dof-sim / sim-23dof-stack
```

## 29DoF 演示线

```text
已有 29DoF policy
  -> deployments/g1_29dof/FSM
  -> deployments/g1_29dof/deploy_mujoco
  -> sim-29dof-mujoco
  -> deploy-29dof-real
```

## 保留边界

项目只默认支持：

```text
Unitree-G1-23Dof-Flat
Unitree-G1-23Dof-Tracking
engines/base_locomotion/deploy/robots/g1_23dof
deployments/g1_29dof
```

如果底层训练引擎内部仍有历史 task 变体，它们属于调试能力，不作为本项目主流程讲解。29DoF 部署层只用于已有策略演示，不反向影响 23DoF 训练配置。
