# TRAIN32 等价原子命名诊断

只使用已有TRAIN32、600001/600011、retained与weak坐标，共128份；无模型调用或训练。
历史GT、评分、模型与坐标不变，另算描述性结果。范围固定为ASP OD1/OD2、GLU OE1/OE2、
PHE/TYR的CD1/CD2与CE1/CE2耦合置换，不包含ASN/GLN元素互换、VAL/LEU/ARG扩展置换、
骨架、跨残基或跨链置换。部分缺失组不动，观测mask保持原样。

对各完整观测歧义组，使用不同残基中观测、非歧义原子的距离作参照，GT15Å邻域，
比较原命名/耦合置换后的距离MAE，严格更低才交换，平局不变。非歧义参照不随其他组
置换而改变。此规则不直接优化lDDT阈值或碰撞分数，不声称是全局最优原子匹配。

记录置换数、原/重命名AA-lDDT及smooth-lDDT损失、坐标梯度范数和余弦变化；
CA坐标/身份与预测坐标完全不变，因此不能把指标变化叫作实际结构改进。
所有结果是开发诊断，不能替换历史结果或放行几何。若实际影响显著，才考虑独立
训练监督干预；不由此宣称主质量差距或骨架问题已经解释。

依据：[AlphaFold命名歧义表](https://github.com/google-deepmind/alphafold/blob/main/alphafold/common/residue_constants.py)
及[Protenix原子置换实现](https://github.com/bytedance/Protenix/blob/main/protenix/utils/permutation/atom_permutation.py)。
本诊断是受限独立实现，不声称复刻Protenix的全部对称处理。
