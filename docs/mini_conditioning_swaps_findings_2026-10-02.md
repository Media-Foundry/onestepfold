# 信息通路消融完成：仅复用 WT trunk 不足，主要缺口在全局 target s/z

**本批结果明确收窄了近似对象：在当前模型、开发面板与代理排序任务上，
需要保留或近似 target-specific 的全局 s/z；target s_inputs 的直接分支不能替代它。**
反过来，在已有完整 target s/z 时，将 s_inputs 换为WT造成的影响很小。
这是条件消融证据，不是“不再需要ESM”或“化学输入没有作用”的结论。

[冻结协议](mini_conditioning_swaps_v1.md) ·
[全部结果、逐位点表和审计](../reports/mini_conditioning_swaps_2026-10-02/README.md)

## 六臂结果

沿用10条开发蛋白×5位点×19非WT替换×2枚噪声。
所有臂都使用原生 **target原子图、参考化学、映射、布局及identity-bound噪声**。
`local`为s[i]与z的第i行/列并集，其余s/z为`complement`。

|条件|s_inputs|s/z|AA-lDDT保真度|19-AA Spearman|Top1一致|两噪声均Top1一致|
|---|---|---|---:|---:|---:|---:|
|Exact|target|target|1|1|100/100|50/50|
|WT-trunk|target|WT|0.974037|**0.252386**|**12/100**|**0/50**|
|Chem-only|WT|WT|0.974035|0.251211|13/100|0/50|
|Target-trunk only|WT|target|0.999999919|**0.999316**|**100/100**|**50/50**|
|Local-only|target|WT complement＋target local|0.975943|0.332368|14/100|1/50|
|Global-only|target|target complement＋WT local|0.997361|**0.953632**|**83/100**|**34/50**|

100是50个位点×2噪声的比较数，不是100条独立蛋白。结构保真度的参照是同噪声
Exact模型坐标，**不是实验突变体真值**。排序仍使用已锁定的父实验骨架CA距离Huber
保持目标，不是binding、真实突变效用或单体无限紧凑化任务。
Chem-only仍有完整WT神经状态，不能理解为没有蛋白上下文。

含WT的20-AA口径没有改变判断：WT-trunk的Spearman=0.250511、Top1=10/100；
Global-only=0.955188、84/100；Target-trunk only=0.999383、100/100。
两种口径及所有逐例数据均保留，没有择优汇报。

## 关键是配对增量，不是单独看Global-only

|配对差（前者减后者）|19-AA Spearman变化|10蛋白bootstrap95%区间|
|---|---:|---:|
|Global-only − WT-trunk|**+0.701246**|**[+0.610766,+0.785563]**|
|Local-only − WT-trunk|+0.079982|[−0.013585,+0.174354]|
|WT-trunk − Chem-only|+0.001175|[−0.010123,+0.008912]|
|Target-trunk only − Chem-only|+0.748105|[+0.661104,+0.825440]|
|Exact − Target-trunk only|+0.000684|[+0.000509,+0.000877]|

Global-only相对WT-trunk的Spearman在 **10/10蛋白均值**上改善。
WT-trunk各蛋白均值仅0.0272–0.5432；Global-only为0.8658–0.9881。
Target-trunk only各蛋白为0.99877–0.99965。

因此，上一批K0仍有高排序保真度，确实不能主要归功于它保留的局部均值：
本次显示，全局target complement具有很大的条件增量作用；保留target s_inputs
却把trunk全部换成WT，不能恢复同样的排序。

这支持“突变相关响应分布在全局s/z”，但**不能进一步定位是ESM、Pairformer哪层
将信息传播出去**。本批没有对上游各层作干预。也不能把这些Spearman差分解释成
某通路贡献了多少百分比的信息；混合输入可能偏离训练分布，通路之间有交互。

## Top1遗憾与真实响应尺度

|条件|平均Top1 regret|按exact任务范围归一化的平均regret|Top5 recall|中心化AA距离响应相对L2误差|
|---|---:|---:|---:|---:|
|WT-trunk|0.081457|0.34555|0.390|0.96332|
|Chem-only|0.079908|0.32932|0.388|0.96330|
|Target-trunk only|0|0|0.996|0.00720|
|Local-only|0.045916|0.28277|0.446|0.91387|
|Global-only|0.002309|0.01558|0.898|0.22251|

距离响应在共同CA非局部距离空间计算，先相对WT，再扣除19-AA均值；
误差是Frobenius范数之比，不是功能保留百分比。
WT-trunk虽然AA-lDDT约0.974、整体结构仍比较接近Exact，
却几乎没有可靠保留AA特异距离响应与候选选择。这再次说明结构接近不等于排序可靠。

## 尾部与几何不随排序均值自动通过

|条件|平均局部CA RMSD，Å|P99，Å|最大，Å|局部>1Å实例/1900|零严重碰撞＋严格所检手性|原通过→新失败|
|---|---:|---:|---:|---:|---:|---:|
|Exact|0|0|0|0|884|0|
|WT-trunk|0.71312|6.63148|15.66260|314|925|161|
|Chem-only|0.71262|6.60849|15.56653|314|923|161|
|Target-trunk only|0.00673|0.16082|0.35894|0|888|3|
|Local-only|0.64390|6.17410|15.32298|283|934|134|
|Global-only|0.23842|2.18558|6.98983|87|865|60|

局部区域、整链拟合框架与旧实验相同，没有为了某臂重选区域或局部重对齐。
6UFE-92继续保留为固定stress case：Global-only最坏为该位点L替换、noise225011；
WT-trunk、Chem-only和Local-only最坏均为该位点S替换、同一噪声。
本批不追加机制追踪，也不从面板中移除它。

Target-trunk only并非逐位相同：平均全链CA RMSD约0.00351Å，
局部最大0.35894Å，AA-lDDT四舍五入到六位为1并不代表坐标完全一致。
它仍有3份新几何失败、6份所检手性错误数增加，不能当作无风险替代模型。
Global-only虽然排序较高，仍有60份新几何失败，局部信息也不能宣称完全可删。

WT-trunk几何汇总通过925/1900高于参考884/1900，却同时有161份新失败，
且AA排序显著失配；本批不是一项改善模型化学或设计效用的训练实验。
碰撞门槛只检查严重重叠，手性仅覆盖已有CA/ILE/THR中心，均不等于完整化学有效。

## 执行与独立复算

直接读取上一批13,005,293,645字节、960份完整conditioning，逐文件SHA核验。
重建原生target化学特征并与旧inventory逐位核对，不重算ESM或C4。
运行时hook禁止Pairformer调用，实际recycle调用 **0**；脚本没有加载ESM。

每次decode重建依赖当前z和target化学的缓存。实际追踪的feature键是：
`relp/ref_pos/ref_charge/ref_mask/ref_element/ref_atom_name_chars/atom_to_token_idx/d_lm/v_lm/pad_info`。
这些之外的序列神经信息来自显式传入的s_inputs/s/z。未读取ESM字段不意味着
没有ESM信息：它已经包含在归档神经状态里。

- 控制器487370；8个GPU worker、8个CPU scorer、collector全部退出0。
- 960次原生化学特征重建，**0次ESM、0次C4、11520次S1**。
- 950突变×6臂×2噪声=11400份mutant输出，加20份WT参考；另100次WT等价控制。
- 所有960条序列的Exact与上一批坐标逐位一致；WT的全部六臂逐位一致。
- 准备及GPU阶段184.64秒，CPU评分60.02秒，总250.69秒；不作端到端速度比较。
- 8个相关测试通过；960坐标包本地哈希及Exact重放通过；2000条Exact任务/几何
  记录与上一批完全一致；600次独立lDDT、全部Spearman复算最大差0；
  60份几何以全原子对距离和行列式独立复算一致。

本地结果：`/home/husrcf/Code/onestepfold_runtime/conditioning_swaps_v1_20261002`。
DiamondHill：`/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/conditioning_swaps_v1_20261002`。
13GB源conditioning仍在同级`functional_response_rank_v1_20261002`，本批未复制或覆盖它。
协议、源文件/权重哈希、控制器终态、所有逐例及逐位点结果均已归档。

## 下一阶段对象已收窄

当前证据不支持“WT C4一次＋target s_inputs＋target chemistry就够了”的直接复用方案。
**完整target s/z或它的有效近似，是当前接口下需要重点保留的对象；仅局部row/col不够。**
但这不要求未来必须逐候选重新执行完整C4，也不证明全局响应无法廉价近似。

Target-trunk only的结果支持后续压缩实验把重点放在s/z，并将WT s_inputs作为一个
明确的开发对照；它没有删除上游target ESM的必要性，因为本批target s/z仍是
用完整target ESM、原生特征与C4预先计算的。

下一项有依据的诊断是**完整s/z的global functional rank**，并保留原始、平衡
block尺度与分别处理s/z的比较。它属于新协议，不与本批混算。
本批收口：未启动global SVD、Jacobian residual、20-query head训练或部署晋升。
