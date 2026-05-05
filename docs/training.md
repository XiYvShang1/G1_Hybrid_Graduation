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

## 视频动作流水线

项目内置了一条面向 Mimic 训练的数据流水线：MP4 视频先恢复为 SMPL 人体动作，再重定向到 G1，最后转换成 mjlab 训练使用的 npz。日常建议先用 dry-run 检查命令：

```bash
python -m cli motion-pipeline path/to/input.mp4 --name demo --person 0 --dry-run
```

确认路径和环境后真实运行：

```bash
python -m cli motion-pipeline path/to/input.mp4 --name demo --person 0
python -m cli train-tracking --motion-file runtime/motion_pipeline/demo/demo_g1.npz
```

如果上游某一步需要单独调试，也可以拆成分步命令：

```bash
python -m cli video-to-smpl path/to/input.mp4 --person 0 --output runtime/example_motion/example_smpl.npz
python -m cli retarget-motion path/to/smpl_motion_folder
python -m cli pkl-to-csv path/to/retarget.pkl --output runtime/example_motion/example_motion.csv
python -m cli csv-to-npz runtime/example_motion/example_motion.csv --output runtime/example_motion/example_motion.npz
python -m cli train-tracking --motion-file runtime/example_motion/example_motion.npz
```

`video-to-smpl` 使用整合后的 GVHMR 源码做 MP4 到 SMPL 的人体运动恢复，`--person` 用于多人视频中的目标选择，输出标准 SMPL npz。`retarget-motion` 会把 SMPL 动作重定向到 G1。CSV 每一行是 `root_xyz + root_quat_xyzw + 23DoF joint_pos`。`csv-to-npz` 会调用 mjlab 的动作回放流程生成训练需要的 `joint_pos`、`joint_vel`、`body_pos_w`、`body_quat_w` 等字段。

动作重定向工具链已经接入到 `motion_pipeline/backends/g1_retarget`，常用入口如下：

```bash
python -m cli install-retarget-poselib
python -m cli filter-smpl-motion path/to/smpl_motion_folder
python -m cli retarget-motion path/to/smpl_motion_folder --correct
python -m cli retarget-motion-phc path/to/smpl_motion_folder
```

这部分依赖 `smpl_sim`、`smplx` 和 SMPL 官方模型参数；SMPL 模型不要提交到仓库，放到 `motion_pipeline/backends/g1_retarget/smpl_retarget/smpl_model/` 本地目录即可。

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
