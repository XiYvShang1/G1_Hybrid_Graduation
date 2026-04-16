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

本项目不是把三个旧仓库粗暴合并成一个大仓，也不是只写一层说明文档，而是采用：

> **壳工程 + 合同层 + 适配层 + 编排层**

的 partial extraction 架构。

三个外部仓库的职责如下：

| 来源仓库 | 在本项目中的角色 | 主要职责 |
|---|---|---|
| `GVHMR2PBHC/` | 动作资产前端 | 视频 / GVHMR / SMPL 结果到 PBHC 兼容动作资产的转换与清洗 |
| `unitree_rl_mjlab/` | 基础运动能力线 | G1 23DoF 速度跟踪、基础 locomotion、MuJoCo 训练与部署参数参考 |
| `PBHC/` | 技能动作与部署语义主线 | 动作重定向、动作跟踪训练、策略导出、MuJoCo / URCI / 实机部署 handoff |

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
   读取 GVHMR2PBHC 的 pt/npz/pkl 转换脚本输出，登记 motion asset。

2. adapters/pbhc
   连接 PBHC retarget / motion tracking / deploy handoff，登记 skill policy。

3. adapters/mjlab
   连接 unitree_rl_mjlab velocity 训练与 deploy.yaml，登记 base locomotion policy。

4. registry
   保存 motion、task、policy 的统一元信息。

5. pipelines
   串联资产构建、训练任务、策略导出和部署交接验证。
```

## 当前边界

- 本项目默认只做**本地编辑、服务器运行**的工程组织。
- 训练仍优先在远程服务器对应仓库内执行。
- 第一阶段不直接调用实机 lowcmd。
- 第一阶段不强行统一 PBHC `.pkl` 与 mjlab `.npz` 的底层格式，而是通过合同层显式记录来源、字段、关节语义和消费链路。

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
  - 输出 GVHMR2PBHC 动作资产构建 wrapper 计划，并向 registry 追加示例动作资产。
- `python -m pipelines.train_base_policy`
  - 输出 mjlab 基础速度策略 wrapper 计划，并向 registry 追加示例基础任务。
- `python -m pipelines.train_skill_policy`
  - 输出 PBHC 技能动作策略 wrapper 计划，并向 registry 追加示例技能任务。
- `python -m cli workflow --config configs/workflows/example_orchestration.yaml`
  - 统一生成 motion/base/skill 三段命令链。
- `python -m cli workflow --config configs/workflows/example_orchestration.yaml --execute --stages motion`
  - 实际执行当前默认可安全执行的 motion 处理阶段，并为其余阶段保留已接通命令入口。

这一步仍然是安全的"可执行骨架"，即：

- 已具备统一入口
- 已具备统一 registry 读取能力
- 已具备路径存在性检查
- 已具备闭环摘要报告
- 已具备三个上游仓库的 wrapper 对象
- 尚未真正调用上游训练命令

## 验收测试

当前阶段的自动化验收命令：

```bash
python -m unittest tests.test_registry_manager
python -m scripts.run_acceptance
```

验收范围当前覆盖 registry / CLI / pipeline 模板层，以及新的 workflow 编排层。`export_policy_bundle.py` 和 `validate_deploy_handoff.py` 当前仍是 metadata 模板入口，不计入真实策略导出或真实部署可用性；`workflow --execute` 也只会真正执行配置中 `execute: true` 的阶段，避免在本地无输入/高成本训练环境下伪造"已全跑完"。

## 目录说明

```text
contracts/   跨仓库统一合同层
adapters/    对 GVHMR2PBHC、PBHC、unitree_rl_mjlab 的封装说明与后续适配代码
pipelines/   新主仓的一键流程入口模板
registry/    动作资产、训练任务、策略产物注册表
configs/     示例配置与 handoff 模板
scripts/     常用状态查看与示例闭环脚本
```
