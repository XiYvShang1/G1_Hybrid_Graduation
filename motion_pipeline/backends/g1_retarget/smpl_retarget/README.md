# G1 SMPL 重定向模块

本目录服务于项目内置动作流水线，用来把标准 SMPL 动作转换成 G1 可用的关节轨迹。

推荐入口：

```bash
python -m cli motion-pipeline path/to/input.mp4 --name demo --person 0
python -m cli retarget-motion path/to/smpl_motion_folder
python -m cli pkl-to-csv path/to/retarget.pkl --output runtime/example_motion/example_motion.csv
```

常用输出会继续交给 `csv-to-npz`，生成动作跟踪训练所需的 npz 文件。
