# G1 动作重定向后端安装说明

这个目录是本项目 `motion_pipeline` 的动作重定向后端。日常不需要直接进入本目录运行脚本，优先使用根目录统一入口：

```bash
python -m cli motion-pipeline path/to/input.mp4 --name demo --person 0
python -m cli retarget-motion path/to/smpl_motion_folder
```

需要单独安装后端依赖时，在目标 Conda 环境中执行：

```bash
pip install -e motion_pipeline/backends/g1_retarget
python -m cli install-retarget-poselib
pip install smplx
```

SMPL 官方模型参数体积较大且受许可限制，不提交到仓库。运行前放到：

```text
motion_pipeline/backends/g1_retarget/smpl_retarget/smpl_model/smpl/
```
