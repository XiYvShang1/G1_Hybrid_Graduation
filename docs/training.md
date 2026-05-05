# 训练说明

项目保留两个训练入口：速度跟踪和动作跟踪。

## 速度跟踪

速度跟踪训练机器人跟随目标线速度和角速度，是基础行走能力训练。

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
python -m cli train-velocity --gpu-ids 0
python -m cli train-velocity --dry-run
```

## 动作跟踪 / Mimic

动作跟踪让策略模仿参考动作文件，适合舞蹈、姿态序列和特定动作片段。

先准备默认动作文件：

```bash
python -m cli prepare-motion
```

开始训练：

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

使用自定义动作文件：

```bash
python -m cli train-tracking --motion-file path/to/motion.npz
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
