# 视频恢复后端环境

建议把视频恢复后端放在独立 Conda 环境中：

```bash
cd motion_pipeline/backends/gvhmr
conda create -y -n gvhmr python=3.10
conda activate gvhmr
pip install -r requirements.txt
pip install -e .
```

模型权重和示例视频不要提交到仓库，放在本地 `inputs/` 或运行时目录即可。
