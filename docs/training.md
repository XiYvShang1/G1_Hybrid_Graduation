# 训练说明

顶层训练命令默认都面向 G1 23DoF。

## 速度跟踪训练

速度跟踪策略学习如何跟随目标线速度和角速度，主要用于基础行走能力。

```bash
python -m cli train-velocity
```

默认任务：

```text
Unitree-G1-23Dof-Flat
```

常用参数：

```bash
python -m cli train-velocity --num-envs 4096
python -m cli train-velocity --gpu-ids 0 1
python -m cli train-velocity --dry-run
```

对应的底层训练命令是：

```bash
python scripts/train.py Unitree-G1-23Dof-Flat --env.scene.num-envs=4096
```

## 动作跟踪 / Mimic 训练

动作跟踪策略学习模仿参考动作文件，适合训练舞蹈、姿态、动作片段等 skill policy。

```bash
python -m cli train-tracking
```

默认任务：

```text
Unitree-G1-23Dof-Tracking
```

默认动作文件：

```text
runtime/example_motion/example_motion.npz
```

训练前先准备默认动作资产：

```bash
python -m cli workflow --config configs/workflows/example_training.yaml --execute --stages motion
```

使用自定义动作文件训练：

```bash
python -m cli train-tracking --motion-file engines/base_locomotion/src/assets/motions/g1_23dof/jilejingtu.npz
```

对应的底层训练命令是：

```bash
python scripts/train.py Unitree-G1-23Dof-Tracking --motion-file src/assets/motions/g1_23dof/jilejingtu.npz --env.scene.num-envs=4096
```

## 训练产物

训练输出默认写入：

```text
engines/base_locomotion/logs/rsl_rl/<experiment>/<date_time>/
```

常见产物：

```text
model_*.pt
policy.onnx
params/env.yaml
params/agent.yaml
videos/
```

## Workflow 编排

只规划默认动作处理、基础速度训练、动作跟踪训练，不启动长任务：

```bash
python -m cli workflow --config configs/workflows/example_training.yaml
```

只执行动作资产准备：

```bash
python -m cli workflow --config configs/workflows/example_training.yaml --execute --stages motion
```

确认 GPU 和依赖环境可用后，再执行训练阶段：

```bash
python -m cli workflow --config configs/workflows/example_training.yaml --execute --stages base skill
```
