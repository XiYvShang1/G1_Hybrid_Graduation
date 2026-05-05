# G1 23DoF Training Engine

This directory contains the project-local training and simulation engine for the
G1 23DoF workflow.

It uses mjlab as the underlying RL/MuJoCo framework, but this repository keeps
only the project-facing G1 23DoF tasks, assets, controller, and simulation entry
points.

Use the repository-level CLI whenever possible:

```bash
python -m cli train-velocity
python -m cli train-tracking
python -m cli play-velocity --checkpoint engines/base_locomotion/logs/rsl_rl/.../model_1000.pt
python -m cli play-tracking --checkpoint engines/base_locomotion/logs/rsl_rl/.../model_1000.pt
python -m cli build-sim
python -m cli sim-stack --network lo
```

Direct engine scripts remain available for debugging:

```bash
python scripts/train.py Unitree-G1-23Dof-Flat --env.scene.num-envs=4096
python scripts/train.py Unitree-G1-23Dof-Tracking --motion-file src/assets/motions/g1_23dof/jilejingtu.npz --env.scene.num-envs=4096
python scripts/play.py Unitree-G1-23Dof-Flat --checkpoint-file logs/rsl_rl/.../model_1000.pt
python scripts/play.py Unitree-G1-23Dof-Tracking --motion-file src/assets/motions/g1_23dof/jilejingtu.npz --checkpoint-file logs/rsl_rl/.../model_1000.pt
```
