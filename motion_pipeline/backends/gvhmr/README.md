# 视频到 SMPL 后端

本目录是 `motion_pipeline` 的视频动作恢复后端，负责从 MP4 中估计人体 SMPL 参数，并把结果交给项目转换器生成标准 SMPL npz。

推荐入口：

```bash
python -m cli video-to-smpl path/to/input.mp4 --person 0 --output runtime/example_motion/example_smpl.npz
python -m cli motion-pipeline path/to/input.mp4 --name demo --person 0
```

权重、输入视频和输出结果不提交到仓库，运行时放在本地 `inputs/`、`outputs/` 或 `runtime/motion_pipeline/`。
