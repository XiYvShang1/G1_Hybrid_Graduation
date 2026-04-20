# G1 混合式动作策略工程

本项目面向 Unitree G1 机器人，组织动作资产、基础运动策略、技能动作策略和部署交接检查，提供一套可扩展的本地工程主链：

```text
动作数据
  -> 动作资产处理
  -> 基础速度策略 / 技能动作策略
  -> 策略产物注册
  -> 部署语义检查
```

## 项目定位

本仓库采用：

> **合同层 + 适配层 + 注册表 + 编排层**

核心目标是把「动作资产、训练任务、策略产物、部署交接」统一到同一套工程规范中，避免能力域之间依赖零散脚本和隐式路径。

| 能力域 | 角色 | 主要内容 |
|---|---|---|
| 动作资产 | 资产输入前端 | 动作数据整理、资产标准化、合法性检查 |
| 基础策略 | 基础运动能力线 | 速度跟踪任务编排、基础策略登记、部署参数追踪 |
| 技能策略 | 技能动作能力线 | 技能动作任务编排、策略登记、部署交接语义检查 |

## 安装

```bash
pip install -r requirements.txt
```

开发测试环境：

```bash
pip install -r requirements-dev.txt
```

训练算法环境：

```bash
pip install -r requirements-algorithms.txt
```

## 常用命令

```bash
python -m cli status
python -m cli check-paths
python -m cli show-closure
python -m cli reset-example-registry
python -m cli workflow --config configs/workflows/example_orchestration.yaml
python -m cli workflow --config configs/workflows/example_orchestration.yaml --execute --stages motion
python -m cli workflow --config configs/workflows/example_training.yaml
```

注册新资产或策略：

```bash
python -m cli add-motion --config configs/assets/example_motion_asset.yaml
python -m cli add-task --config configs/tasks/example_base_velocity_task.yaml
python -m cli add-policy --config configs/policies/example_policy_bundle.yaml
```

## 目录说明

```text
contracts/   跨能力域统一合同层
adapters/    motion/base/skill 三类能力域的入口封装
engines/     已迁入的基础运动与技能动作训练算法
pipelines/   项目内动作处理、训练登记、策略导出和部署检查入口
registry/    动作资产、训练任务、策略产物注册表
configs/     示例配置和部署交接模板
runtime/     本地运行产物和编排报告
scripts/     常用状态查看与验收脚本
tests/       registry 与 CLI 的回归测试
```

## 当前能力边界

- 已具备统一 CLI 入口。
- 已具备 motion / task / policy registry 读写能力。
- 已具备路径存在性检查和最小闭环报告。
- 已具备 motion / base / skill 三个能力域的本地 adapter。
- 基础运动训练算法已经迁入 `engines/base_locomotion`。
- 技能动作跟踪训练算法已经迁入 `engines/skill_tracking`。
- workflow 默认仍不自动执行高成本训练，需要在配置里显式开启对应阶段。
- 未完成离线 handoff 校验的策略不应标记为 deploy-ready。

## 训练入口

基础运动训练入口：

```bash
cd engines/base_locomotion
python scripts/train.py Unitree-G1-23Dof-Flat --env.scene.num-envs=128
```

技能动作跟踪训练入口：

```bash
cd engines/skill_tracking
python humanoidverse/train_agent.py +simulator=isaacgym +exp=motion_tracking +terrain=terrain_locomotion_plane project_name=MotionTracking num_envs=128 +obs=motion_tracking/benchmark +robot=g1/g1_23dof_lock_wrist +domain_rand=dr_nil +rewards=motion_tracking/main experiment_name=hybrid_debug robot.motion.motion_file=../../runtime/example_motion/example_motion.pkl seed=1 +device=cuda:0
```

## 验收

```bash
python -m unittest tests.test_registry_manager
python -m unittest tests.test_cli_smoke
python -m scripts.run_acceptance
```

或使用：

```bash
make check
make test
make acceptance
```
