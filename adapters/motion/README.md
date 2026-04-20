# 动作资产适配层

该适配层用于接入项目内动作资产处理能力，并输出统一的 motion 登记信息。

## 适配边界

- 输入：原始动作数据或中间动作文件。
- 输出：标准化后的动作资产登记项。
- 当前阶段：优先完成路径、字段和可执行入口登记。

## 默认入口

- `pipelines/process_motion_asset.py`
- `pipelines/build_motion_asset.py`
