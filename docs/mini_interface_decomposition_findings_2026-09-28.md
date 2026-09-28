# 完整接口误差分解：control 的主要偏差在 diffusion 之前

2026-09-28。本轮完成两个已保存失败点：control_a1_s1、8bzn_a1_s1，α=1e−3，C4/S1、原三个随机方向和五个 h。原生图、噪声、布局、模型与目标不变。没有继续扫描 α、增加目标或训练模型。

[预先锁定协议](mini_interface_decomposition_v1.md) · [全部 30 行分解](../reports/mini_interface_decomposition_2026-09-28/report.md) · [CPU 审计](../reports/mini_interface_decomposition_2026-09-28/audit.json) · [embedding 数值参照](../reports/mini_interface_decomposition_2026-09-28/embedding_reference.json)

## 接口切分通过了等价性检查

接口 b 包含 s_inputs、s、z 和 ref_pos/ref_charge/ref_mask/ref_element/ref_atom_name_chars。下游由原始参考化学字段重建 d_lm/v_lm/pad_info，固定 relp、atom_to_token_idx 和 ref_space_uid。实际 diffusion 读取审计未发现遗漏的可微特征；五个化学字段都有贡献，没有把 d_lm 再作为独立变量重复计入。

| 检查 | control | 8BZN |
|---|---:|---:|
| 切分前后坐标 | 逐位一致 | 逐位一致 |
| 基点及全部 ±h 坐标与旧归档 | 逐位一致 | 逐位一致 |
| 链式 AD 重建相对 L2 误差 | 4.19e−10 | 1.33e−9 |

固定 w 为旧归档中新目标的坐标梯度，KL 的直接 q 梯度单列。a 使用此次固定线性投影的端到端 AD；它与旧标量 loss 的 AD 存在小量差异，未隐藏或用来覆盖旧结果：control 方向 0 相差 1.16e−8，8BZN 方向 0 相差 −6.42e−10。两次完整 q 梯度的最大元素差分别为 4.25e−7、2.04e−8。当前分解中的链式 AD 与直接 AD 则满足上表重建精度。尚未独立归因这项小差异，不把它说成逐位相等。

## control：15/15 行主要偏差在接口之前

定义 a 为端到端 AD，m 为接口差分乘下游 VJP，d 为坐标差分乘固定 w。则 d−a=(m−a)+(d−m)。以下保留你指定的高信号方向 0：

| h | a | m | d | m−a，上游偏差 | d−m，下游偏差 |
|---:|---:|---:|---:|---:|---:|
| .3 | −1.02070e−4 | +4.66092e−5 | +4.90504e−5 | +1.48679e−4 | +2.44118e−6 |
| .1 | −1.02070e−4 | −4.74830e−4 | −4.71546e−4 | −3.72760e−4 | +3.28411e−6 |
| .03 | −1.02070e−4 | −5.38547e−4 | −5.49159e−4 | −4.36477e−4 | −1.06123e−5 |
| .01 | −1.02070e−4 | −2.19942e−3 | −2.13309e−3 | −2.09735e−3 | +6.63343e−5 |
| .003 | −1.02070e−4 | −5.04378e−3 | −5.01642e−3 | −4.94171e−3 | +2.73660e−5 |

不仅方向 0，control 全部 15 行均有 |m−a|>|d−m|。这把主要定位范围收缩到 logits→ESM/输入特征/Pairformer→完整接口，而非最终 loss 曲率或仅 diffusion。接口 secant 的分量中 z 投影明显，但这不能直接指定为 z 的某个算子错误，也不能区分 ESM 与四轮 Pairformer 各自贡献。

8BZN 不可套用同一单一结论：12/15 行上游偏差较大；方向 1 的 h=.03/.01、方向 2 的 h=.1 下游偏差相当或更大。例如方向 1、h=.01：上游 −6.84e−6，下游 −5.91e−5。应保留两侧问题。以上为数值与局部线性化偏差，不是“梯度错误比例”或 bug 定罪。

## 局部参照：进入 ESM Transformer 前已有数值差分问题

分解完成后，仅对 q→softmax(q)→pW 做小段参照，不执行 Transformer 或 folding。使用同一 q、v、h 和实际 checkpoint 的 20 行 token weights。checkpoint 存储为 FP16，原生模型加载到 FP32；参照相应先转 FP32，再提升到 FP64。FP64 不恢复权重训练精度，也不改变模型。运行设备为 MI250，matmul_precision=highest、allow_tf32=False。

control 方向 0，向量 FD 相对解析 FP64 tangent 的 L2 误差：

| h | FP32 运算 | FP64 运算、FP64 扰动 | FP64 运算、保留原 FP32 q± 舍入 |
|---:|---:|---:|---:|
| .3 | 1.43% | 2.66e−5 | 3.22e−5 |
| .1 | 4.40% | 2.95e−6 | 5.01e−5 |
| .03 | 14.45% | 2.66e−7 | 1.70e−4 |
| .01 | 34.97% | 2.96e−8 | 5.12e−4 |
| .003 | 82.14% | 3.86e−9 | 1.62e−3 |

8BZN 方向 0 同样从约 1.28% 增到 70.10%；FP64 参照收敛到约 4.94e−9。六个方向的小段 FP64 真正 forward-mode torch.func.jvp 与解析式相对误差约 2–3e−13，JVP/VJP 投影差约 1e−16。FP32 小段 JVP 与解析式误差约 1e−4，远小于小 h 的差分误差，但仍不是严格零误差。

因此已经有证据支持：当前 near-hard、原步长下，softmax/pW 的前向浮点运算足以污染局部差分，不能把 end-to-end FD 失败直接当成 backward 错误。保留 FP32 q±、仅提升小段运算精度的参照也表明，此处主要误差不能只算给 logits 扰动的量化。

限制：尚未证明这一小段误差能解释后续全部坐标响应，未测 ESM Transformer 或 Pairformer 的 FP64/JVP，也未认证完整输入梯度。此处使用 tangent 对齐的固定 embedding 投影只作局部 JVP/VJP 交叉检查，不替换原随机 logits 方向或端到端 FD 标准。

参照脚本第一次读取 checkpoint 时遗漏了存储 FP16→运行 FP32 的转换，被 dtype 检查中止；失败日志已保留。修正后只重跑了小段运算，没有重跑折叠任务。

## 审计、存档与下一步

17 项聚焦测试通过。CPU 独立重算全部 30 行接口/坐标投影与分解，最大数值差 3.47e−18。大接口差分张量与基点/VJP 保存在 DiamondHill：
`/media/PM982/onestepfold/mini_interface_decomposition_v1_20260928/`，哈希绑定于 audit.json；本地和 Git 保存紧凑报告、锁定输入、脚本与小段 embedding 权重证据。GitNexus 索引已刷新到 09f0e82b；图覆盖未展示完整动态调用，实际依赖结论来自源码和运行时读取审计。

本轮到此停止。下一次应沿 control 同一失败点进一步切分 ESM 输出与 Pairformer 的响应，或在已定位局部路径建立精度参照；不应重开大矩阵或训练 diffusion。8BZN 的下游偏差另行保留。

hard 基线几何不合格与导数认证失败仍是两项独立事实。继续保留旧 absolute/nonregression 阈值与失败；几何合格不是数学导数审计的前提，部署仍须联合验收。当前部署不通过。
