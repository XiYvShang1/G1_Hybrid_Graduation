# G1 23DoF 训练引擎

这个目录是顶层 G1 23DoF 项目内置的 MuJoCo/mjlab 训练与仿真引擎。

日常使用优先走仓库根目录的统一 CLI：

```bash
python -m cli train-velocity
python -m cli train-tracking
python -m cli play-velocity --checkpoint engines/base_locomotion/logs/rsl_rl/.../model_1000.pt
python -m cli play-tracking --motion-file runtime/example_motion/example_motion.npz --checkpoint engines/base_locomotion/logs/rsl_rl/.../model_1000.pt
python -m cli build-sim
python -m cli sim-stack --network lo
```

调试时也可以直接运行引擎脚本：

```bash
python scripts/train.py Unitree-G1-23Dof-Flat --env.scene.num-envs=4096
python scripts/train.py Unitree-G1-23Dof-Tracking --motion-file src/assets/motions/g1_23dof/jilejingtu.npz --env.scene.num-envs=4096
python scripts/play.py Unitree-G1-23Dof-Flat --checkpoint-file logs/rsl_rl/.../model_1000.pt
python scripts/play.py Unitree-G1-23Dof-Tracking --motion-file src/assets/motions/g1_23dof/jilejingtu.npz --checkpoint-file logs/rsl_rl/.../model_1000.pt
```

顶层项目默认只使用 G1 23DoF 的速度跟踪和动作跟踪任务。引擎目录里可能还有其他机器人或任务变体，它们属于底层能力，不属于默认毕业项目工作流。
