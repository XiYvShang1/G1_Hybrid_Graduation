# 第三方组件与本地资产说明

本项目以 G1 23DoF 训练、动作数据流水线和部署演示为主线，仓库内集成了若干后端模块用于形成完整闭环。

## 已集成代码

- `engines/base_locomotion/`：23DoF 训练、回放、仿真和控制器基础引擎。
- `motion_pipeline/backends/gvhmr/`：视频到 SMPL 的动作恢复后端，保留其许可证文件。
- `motion_pipeline/backends/g1_retarget/`：SMPL 到 G1 的动作重定向后端，保留其许可证文件。
- `deployments/g1_29dof/`：29DoF 已训练策略部署演示层。

## 不提交的大文件

以下内容通常体积较大或存在单独许可限制，不放入 Git 仓库：

- 视频输入、渲染输出、训练日志和临时运行文件。
- GVHMR checkpoints 和人体模型权重。
- SMPL/SMPL-X 官方模型参数。
- 用户自己的 `.env`、本机 Conda 路径和私有部署配置。

本地路径模板见：

```text
configs/runtime.example.env
```

## 项目边界

根目录 CLI 只暴露本项目稳定入口：视频动作流水线、23DoF 速度跟踪训练、23DoF 动作跟踪训练、23DoF 仿真部署和 29DoF 演示部署。底层后端中保留的调试脚本不作为项目主流程入口。
