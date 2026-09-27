# Scratch TRAIN4 监督对照

两臂同随机初始化、输入、优化器、顺序和噪声；仅 smooth-lDDT 项不同。
这只评估小集记忆能力，不评估泛化或最低 1% 尾部。

| 臂 | 停止曝光/蛋白 | 停止原因 | 联合通过 | 作业内耗时秒 |
| --- | ---: | --- | --- | ---: |
| baseline | 500 | joint_capacity_pass | True | 1171.7 |
| smooth_lddt | 550 | joint_capacity_pass | True | 1284.3 |

完整同曝光比较见 matched_exposure_curves.csv；提前停止后不外推。

下一步先人工审阅逐目标曲线和化学指标，再决定是否进入 TRAIN32。
