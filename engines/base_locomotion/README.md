# G1 23DoF Training Engine

This directory contains the integrated MuJoCo/mjlab training and simulation
engine used by the top-level G1 23DoF project.

The project-level CLI in the repository root is the preferred entrypoint:

```bash
python -m cli train-velocity
python -m cli train-tracking
python -m cli play-velocity --checkpoint engines/base_locomotion/logs/rsl_rl/.../model_1000.pt
python -m cli play-tracking --motion-file runtime/example_motion/example_motion.npz --checkpoint engines/base_locomotion/logs/rsl_rl/.../model_1000.pt
python -m cli build-sim
python -m cli sim-stack --network lo
```

Direct engine commands remain available for debugging:

```bash
python scripts/train.py Unitree-G1-23Dof-Flat --env.scene.num-envs=4096
python scripts/train.py Unitree-G1-23Dof-Tracking --motion-file src/assets/motions/g1_23dof/jilejingtu.npz --env.scene.num-envs=4096
python scripts/play.py Unitree-G1-23Dof-Flat --checkpoint-file logs/rsl_rl/.../model_1000.pt
python scripts/play.py Unitree-G1-23Dof-Tracking --motion-file src/assets/motions/g1_23dof/jilejingtu.npz --checkpoint-file logs/rsl_rl/.../model_1000.pt
```

The top-level repository scopes this engine to the G1 23DoF graduation project.
Other robot/task variants may exist in the engine tree, but they are not part of
the default project workflow.
