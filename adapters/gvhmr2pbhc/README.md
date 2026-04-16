# 动作资产适配层

该适配层用于接入动作资产处理能力，并向主仓输出统一的 motion 登记信息。

## 适配边界

- 输入：原始动作数据（如 `.pt`、`.npz`、中间 `.pkl`）。
- 输出：标准化后的动作资产登记项。
- 当前阶段：优先完成路径、字段和可执行入口登记，不复制外部训练内核。

## 默认入口（可按需替换）

- `Converter_V4.py`
- `convert_fit_motion_V2.py`
- `modify_motion.py`
- `motion_interpolation_pkl.py`
- `motion_readpkl_V2.py`
