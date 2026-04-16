/usr/bin/bash: /home/xiyv/miniconda3/lib/libtinfo.so.6: no version information available (required by /usr/bin/bash)
# G1 混合式动作策略项目

本项目是面向 Unitree G1 机器人的混合工程主仓，用于把工作区内已有的三条能力线组织成一条清晰、可扩展的技术主链：

```text
动作数据 / 视频源
  -> 动作重定向与动作资产生成
  -> 基础速度跟踪训练 / 技能动作跟踪训练
  -> 策略产物注册
  -> 部署语义恢复与仿真验证
```

## 项目定位

本仓库是独立的 G1 混合式动作策略工程，不是对任何单一项目的复制或镜像。整体采用：

> **壳工程 + 合同层 + 适配层 + 编排层**

的架构设计，核心目标是把「动作资产、训练任务、策略产物、部署交接」统一到同一套工程规范中。

当前版本聚焦以下 3 类能力：

| 能力域 | 在本项目中的角色 | 主要内容 |
|---|---|---|
| 动作资产能力 | 资产输入前端 | 动作数据整理、资产标准化、合法性检查 |
| 基础策略能力 | 基础运动能力线 | 速度跟踪任务编排、基础策略登记、部署参数追踪 |
| 技能策略能力 | 技能动作能力线 | 技能动作任务编排、策略登记、部署交接语义检查 |

## 环境依赖与安装

### 基础依赖

- Python 3.8+
- NumPy
- PyYAML

### 快速安装

```bash
# 克隆本仓库
git clone https://github.com/XiYvShang1/G1_Hybrid_Graduation.git
cd G1_Hybrid_Graduation

# 安装基础依赖
pip install -r requirements.txt
```

### 可选依赖（根据使用的模块）

如果你需要跑完整训练或部署链路，请在工作区准备对应能力域的运行环境（仿真依赖、训练依赖、部署依赖），并将相关脚本路径配置到 `registry/` 与 `configs/` 中。

开发测试环境建议安装：

```bash
pip install -r requirements-dev.txt
```

## 第一阶段目标

第一阶段只做新主仓骨架和合同模板，不重写旧仓库训练框架：

1. 建立统一动作资产注册方式。
2. 建立统一任务注册方式。
3. 建立统一策略产物注册方式。
4. 建立训练到部署的交接清单。
5. 为后续一键 pipeline 和项目展示提供稳定目录结构。

## 推荐工作流

```text
1. adapters/gvhmr2pbhc
   负责动作资产输入与标准化，登记 motion asset。

2. adapters/pbhc
   负责技能策略任务入口与部署语义检查，登记 skill policy。

3. adapters/mjlab
   负责基础策略任务入口与部署参数追踪，登记 base locomotion policy。

4. registry
   保存 motion、task、policy 的统一元信息。

5. pipelines
   串联资产构建、训练任务、策略导出和部署交接验证。
```

## 当前边界

- 本项目默认只做**本地编辑、服务器运行**的工程组织。
- 训练仍优先在远程服务器对应仓库内执行。
- 第一阶段不直接调用实机 lowcmd。
- 第一阶段不强行统一不同能力域中的底层资产格式（如 `.pkl`、`.npz`），而是通过合同层显式记录来源、字段、关节语义和消费链路。

## 第二阶段升级内容

当前仓库已经升级出最小可执行骨架：

- `python -m cli status`
  - 读取 `registry/` 下的 motion / task / policy 注册表并输出项目状态。
- `python -m cli check-paths`
  - 检查 registry 中记录的关键路径在当前工作区内是否存在。
- `python -m cli show-closure`
  - 输出当前项目的最小闭环报告。
- `python -m cli add-motion --config <yaml>`
  - 从配置文件向 registry 注册动作资产；同 ID 会覆盖更新，不会重复膨胀。
- `python -m cli add-task --config <yaml>`
  - 从配置文件向 registry 注册训练任务；同 ID 会覆盖更新，不会重复膨胀。
- `python -m cli add-policy --config <yaml>`
  - 从配置文件向 registry 注册策略产物；同 ID 会覆盖更新，不会重复膨胀。
- `python -m cli reset-example-registry`
  - 将 registry 重置为当前示例配置，方便反复测试。
- `python -m pipelines.build_motion_asset`
  - 输出动作资产构建 wrapper 计划，并向 registry 追加示例动作资产。
- `python -m pipelines.train_base_policy`
  - 输出基础速度策略 wrapper 计划，并向 registry 追加示例基础任务。
- `python -m pipelines.train_skill_policy`
  - 输出技能动作策略 wrapper 计划，并向 registry 追加示例技能任务。
- `python -m cli workflow --config configs/workflows/example_orchestration.yaml`
  - 统一生成 motion/base/skill 三段命令链。
- `python -m cli workflow --config configs/workflows/example_orchestration.yaml --execute --stages motion`
  - 实际执行当前默认可安全执行的 motion 处理阶段，并为其余阶段保留已接通命令入口。

这一步仍然是安全的"可执行骨架"，即：

- 已具备统一入口
- 已具备统一 registry 读取能力
- 已具备路径存在性检查
- 已具备闭环摘要报告
- 已具备三个能力域的 wrapper 对象
- 尚未真正调用高成本训练命令

## 验收测试

当前阶段的自动化验收命令：

```bash
python -m unittest tests.test_registry_manager
python -m unittest tests.test_cli_smoke
python -m scripts.run_acceptance
```

如果你偏好统一命令，可以直接使用：

```bash
make check
make test
make acceptance
```

验收范围当前覆盖 registry / CLI / pipeline 模板层，以及新的 workflow 编排层。`export_policy_bundle.py` 和 `validate_deploy_handoff.py` 当前仍是 metadata 模板入口，不计入真实策略导出或真实部署可用性；`workflow --execute` 也只会真正执行配置中 `execute: true` 的阶段，避免在本地无输入/高成本训练环境下伪造"已全跑完"。

## 目录说明

```text
contracts/   跨能力域统一合同层
adapters/    各能力域运行入口的封装说明与后续适配代码
pipelines/   新主仓的一键流程入口模板
registry/    动作资产、训练任务、策略产物注册表
configs/     示例配置与 handoff 模板
scripts/     常用状态查看与示例闭环脚本
```

## 致谢与技术参考

本项目为独立工程实现，仓库结构、合同层与编排方式均按本项目目标自行设计。

在方法论与工程实践上，参考了以下公开资料（按主题列出）：

- 动作重建与动作资产处理：
  - [GVHMR](https://github.com/zju3dv/GVHMR)
  - [GVHMR2PBHC](https://github.com/Book15011/GVHMR2PBHC)
- 动作技能训练与部署语义：
  - [PBHC / KungfuBot](https://kungfu-bot.github.io/)
  - [PBHC 论文](https://arxiv.org/abs/2506.12851)
- 强化学习训练与仿真基础：
  - [mjlab](https://github.com/mujocolab/mjlab)
  - [ASAP](https://github.com/LeCAR-Lab/ASAP)
  - [RSL_RL](https://github.com/leggedrobotics/rsl_rl)
  - [MuJoCo](https://github.com/google-deepmind/mujoco)
