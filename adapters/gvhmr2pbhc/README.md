# GVHMR2PBHC 适配层

该适配层负责把 `GVHMR2PBHC/` 中的视频动作后处理能力纳入本毕设主仓。

## 适配边界

- 输入：GVHMR `.pt`、SMPL/AMASS 风格 `.npz`、中间 motion `.pkl`。
- 输出：可被 PBHC retarget / motion tracking 消费的动作资产登记项。
- 第一阶段只登记路径和字段，不复制转换脚本。

## 重点旧仓库入口

- `GVHMR2PBHC/Converter_V4.py`
- `GVHMR2PBHC/convert_fit_motion_V2.py`
- `GVHMR2PBHC/modify_motion.py`
- `GVHMR2PBHC/motion_interpolation_pkl.py`
- `GVHMR2PBHC/motion_readpkl_V2.py`
