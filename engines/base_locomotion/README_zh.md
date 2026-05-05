# G1 23DoF 训练引擎

这个目录是项目内置的 G1 23DoF 训练与仿真引擎。

底层强化学习、MuJoCo 环境和任务注册机制依赖 mjlab，但当前仓库只保留面向本项目的 G1 23DoF 任务、机器人资产、部署控制器和仿真入口。

日常使用建议走项目根目录 CLI：

```bash
python -m cli train-velocity
python -m cli train-tracking
python -m cli play-velocity --checkpoint engines/base_locomotion/logs/rsl_rl/.../model_1000.pt
python -m cli play-tracking --checkpoint engines/base_locomotion/logs/rsl_rl/.../model_1000.pt
python -m cli build-sim
python -m cli sim-stack --network lo
```

如果需要调试底层引擎，也可以直接运行：

```bash
python scripts/train.py Unitree-G1-23Dof-Flat --env.scene.num-envs=4096
python scripts/train.py Unitree-G1-23Dof-Tracking --motion-file src/assets/motions/g1_23dof/jilejingtu.npz --env.scene.num-envs=4096
python scripts/play.py Unitree-G1-23Dof-Flat --checkpoint-file logs/rsl_rl/.../model_1000.pt
python scripts/play.py Unitree-G1-23Dof-Tracking --motion-file src/assets/motions/g1_23dof/jilejingtu.npz --checkpoint-file logs/rsl_rl/.../model_1000.pt
```
