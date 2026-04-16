# 毕设图表与展示资产

该目录用于归档毕业设计中需要复用的图表、流程图、截图和实验展示素材。

建议后续按以下方式组织：

```text
thesis-assets/
├─ figures/        论文流程图、系统架构图、训练闭环图
├─ screenshots/    训练、仿真、pipeline 运行截图
├─ tables/         任务表、策略表、部署 handoff 表
└─ exports/        draw.io、svg、png 等导出文件
```

图表主线建议围绕：

1. 动作数据到机器人动作资产。
2. 基础速度训练与技能动作训练双路线。
3. 策略注册与部署语义恢复。
4. obs/action/default/scale 到 hybrid command 的恢复链。
