# 完整 s/z functional rank：共享 3–5 维不足，平均排序不能替代尾部

2026-10-02。本批完整运行并收口；协议为 [mini_global_response_rank_v1.md](mini_global_response_rank_v1.md)。

**在本开发面板与当前 oracle PCA 构造下，全局共享 K5 并不能保留上一轮局部 K5 的高功能保真度。**
raw K5 的 19-AA Spearman 为 **0.8240**，Top1 为 **53/100**；K8 为 **0.8939、69/100**。
K12 的平均相关性达到约 0.95，但仍有选择错误、严重局部偏移和新增几何失败。
这不支持直接训练一个全局共享五维 head，也不支持把 K12 当成已通过的模型；
它没有否定一次 WT trunk 后预测并行 hard-AA 全局响应的总体方向。

## 固定对象、两个参照与实际成本

- 同一 10 条 TRAIN 开发蛋白、50 位点、每位点 19 个 non-WT 替换；950 个 mutant 与 10 个共享 WT。
- 公开 Mini-ESM v0.5.0，原生 FP32，225001/225011 两枚身份绑定噪声；受控 stable-Euler S1。
- 复用此前 960 份完整 conditioning（约 13.005 GB），实际 **0 次 ESM、0 次 C4/recycle**；没有训练、Jacobian 或新候选。
- 五种方案 × 十个 K，**完整替换 s/z**；所有 rank 方案使用 WT `s_inputs` 和真实 target 原子图/reference chemistry。
- Exact：target `s_inputs,s,z`。Baseline：WT `s_inputs`＋完整 target `s,z`，即上一批 target-trunk-only。
- 同时给出对 Exact 的总误差和对 Baseline 的纯压缩误差。Baseline 本身仍有小幅坐标变化及 3 个相对 Exact 的新增几何失败。
- K0 在 raw/balanced/separate-both 间完整张量相同，验证后共享解码；其余均实际执行。总计 **95,020 次 S1 调用**，避免 3,800 次重复调用。
- 8 个 GPU worker、32 个 CPU scorer、collector 均退出 0；准备＋GPU **853.52 s**，评分 **201.05 s**，控制器总墙钟 **1,076.64 s**。单 worker 最大 allocated GPU 内存约 **3.842 GB**。

这些是已有完整状态的诊断吞吐，不是从 WT 输入开始的端到端加速。源 teacher 的 target ESM/C4 成本并没有消失。

## 全局共享 raw 曲线

以下 Spearman、Top1、regret 均对 Exact 的固定 parent-GT CA 距离 Huber 代理排序。
Top1 分母是 50 位点 × 2 噪声，不是 100 个独立蛋白；结构实例分母为 1,900。
“新增失败”只指原先通过零严重碰撞＋严格所检手性的实例变为不通过，不是全面化学判据。

|K|Spearman|Top1 /100|两噪声均 Top1 /50|平均 Top1 regret|局部 RMSD >1Å /1900|新增失败：对 Exact / Baseline|
|---:|---:|---:|---:|---:|---:|---:|
|0|0.286596|14|1|0.074344|234|118 / 120|
|5|0.824000|53|18|0.013165|43|74 / 77|
|8|0.893860|69|27|0.005495|37|62 / 64|
|12|0.950754|72|27|0.006230|30|36 / 37|
|15|0.980088|84|37|0.000964|17|23 / 23|
|18|0.999316|100|50|0|0|3 / 0|

全部 K=0,1,2,3,5,8,10,12,15,18 与五种方案见[完整曲线](../reports/mini_global_response_rank_2026-10-02/report.md)、
[图](../reports/mini_global_response_rank_2026-10-02/global_rank_curves.png)及机器可读报告。
K5 相关性的蛋白 bootstrap 95% 区间为 **[0.76944,0.86937]**；K8 为 **[0.85675,0.92779]**；
K12 为 **[0.92967,0.96896]**。重采样单位为 10 条蛋白，10000 次，不将位点/噪声当独立蛋白。

重要的非单调性也原样保留：raw K10 Top1 为 76/100，K12 反而为 72/100；
K12 的 regret 也高于 K8。更多欧氏能量不保证每个有限排序、最优选择或几何指标单调改善。

K0 这次是真正的整块共同 mutant 均值：没有 exact target global complement，也没有 target `s_inputs`。
其相关性从上一轮局部 K0 的约 0.959 降到 0.287，进一步说明此前高保真结果有 exact complement 兜底。
但 K0 仍有各 AA 的 target chemistry，且共同均值取自全部 19 个 teacher；它不是 WT-only 推理。

K18 对 **Baseline** 是坐标逐位一致、Spearman=1、无新增失败。
对 Exact 仍为 0.999316、3 个新增失败，来自已知 `s_inputs` 替换效应，不能命名为完整 rank 的误差。

## 权重平衡与 s/z 容量的区别

raw 使用 Gs+Gz；balanced 使用 Gs/Es+Gz/Ez，Es/Ez 是位点全部 WT-anchored response 的固定总能量（中心化之前）。
分别压缩采用各自基底，separate-both 最多有 2K 个不同 AA 系数方向，不是共享 K 的等容量方案。

|K5 方案|Spearman|Top1 /100|局部 RMSD均值 Å|新增几何失败对 Exact|
|---|---:|---:|---:|---:|
|raw shared|0.824000|53|0.226166|74|
|block-balanced shared|0.807368|50|0.249737|73|
|separate-both|0.849316|63|0.218407|68|
|rank s＋exact z|0.921526|81|0.155670|47|
|exact s＋rank z|0.920877|68|0.111185|55|

本面板中，z 占 WT-anchored raw 总能量的位点平均约 **94.29%**，范围 **67.12%–99.47%**，确有数值支配。
但平衡并未挽救低 K：K5 balanced−raw 的 Spearman 均差 **−0.01663**，蛋白 bootstrap 区间 **[−0.03516,+0.00119]**。
不能声称 raw 已显著优于 balanced，也不能说平衡后五维变得足够。没有按某个更有利指标事后挑方案。

K0 分块结果尤其有信息：

|输入|Spearman|Top1 /100|局部 >1Å /1900|最大局部 RMSD Å|
|---|---:|---:|---:|---:|
|mean s＋exact z|0.856596|68|59|17.1342|
|exact s＋mean z|0.441526|32|200|8.5476|

保留 z 的 AA-specific 信息对排序更有帮助，但 s 的信息不能忽略；它的低能量尾部可以伴随很大的局部坐标变化。
这是条件干预比较，不是两块的信息百分比，也不能从这里单独指定某个 decoder 算子的机制。
两种单块 K5 都约 0.921，而同时压缩只有约 0.824；不能把某块保持 exact 的表现当作完全压缩 head 的成绩。

中心化谱仅作为描述：raw K5/K8/K12 平均累计能量 **82.22%/91.31%/96.78%**，位点 median K95=11；
balanced 为 **72.93%/84.83%/93.61%**，median K95=13；s、z 各自 median K95=14、10。
即使 raw K12 平均保留近 97% 欧氏能量，也没有保证最佳 AA 选择与局部安全。

## 尾部和几何不能被均值覆盖

raw K5 的平均 AA fidelity 为 **0.996619**、平均局部 RMSD 为 **0.226166 Å**，
但最大局部 RMSD 是 **15.5005 Å**。43 个 >1Å 实例中，36 个来自冻结压力位点 **6UFE-92**，
其余分布于 1A8R-220、2DT5-209、6UFE-85、2SAK-100。
K8 的 37 个尾部中 36 个来自 6UFE-92；K12 的 30 个和 K15 的 17 个全部来自该位点。
K12/K15 最大偏移仍为 **6.7527/2.9670 Å**。未排除、未补跑、未根据结果改变预算。

原 Exact 仅 **884/1900** 通过当前零严重碰撞＋严格所检手性，Baseline 为 888。
raw K5 的总通过数为 **885**，看似接近 Exact，却同时新增 **74** 个失败；净计数掩盖了改善/退化转换。
完整逐例表保留严重原子对计数、手性、penetration、结构/接触指标及对两个参照的变化。
这些结构 fidelity 指标对照的是模型 hard endpoint，并非突变实验 GT；排序目标也是 parent 结构代理，不是设计效用或亲和力。

## 审计、产物与结论边界

- 960 个 Exact 以及 960 个 Baseline endpoint 重放均与上一批坐标逐位相同；化学身份、原子顺序、bonds、reference 检查通过。
- 全部 50 位点由独立 NumPy FP64 分块累积 Gram、eigh 和 projector 复算。
  最大 Gram 相对误差 **1.71e−14** 以下，累计能量误差 **4.22e−15** 以下。
- 五种方案共 4,750 次 K18 实际重建/解码检查，conditioning 最大误差 **2.274e−13**，坐标最大误差 **0**。
- 相关单元测试 **10 项通过**，包括与直接矩形 SVD 一致、zero-energy block、未压缩块精确保持与 K0 等价。
- 独立复核 960 份坐标包、4000 项参照 task/geometry、5200 项 lDDT、20400 项排序全部一致；SHA 清单见审计文件。原始坐标、完整状态保存在 Git 外，位置见 `storage.json`。

当前结论是：**这套全局欧氏 PCA 共享 3–5 维构造，在已测开发面板上不足以保留 hard-AA 功能响应。**
它不是所有非线性低维表示均不存在的证明；本实验均值、基底、系数读取了全部真实 teacher，
仍属于 in-sample oracle 诊断，并没有检验从 WT context 预测这些量的可学习性，
也不是所有可学习压缩器的功能上界。

一次 WT C4 后生成全局 response field 的方向仍可保留；不应直接把 head 的 AA 轴锁为五维，
也不应仅因平均 rho 接近 0.95 就选 K12。Jacobian residual 仍是候选诊断，
但本批没有启动它、训练 propagator、修改模型权重或宣称部署/设计通过。完整曲线收口，等待下一项明确的方法决定。
