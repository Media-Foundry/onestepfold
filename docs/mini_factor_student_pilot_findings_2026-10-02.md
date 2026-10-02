# 首个 factor-only student：新蛋白上 oracle 空间压缩仍有效，当前小网络没有学成替代

2026-10-02。本批teacher生成、两次固定预算训练、终点评估和独立审计均已完成，正式收口。
[训练协议](mini_factor_student_pilot_v1.md)、[新数据协议](mini_factor_student_teachers_v1.md)、
[完整表](../reports/mini_factor_student_pilot_2026-10-02/report.md)。
R24补充结论另见[报告](mini_spatial_rank24_findings_2026-10-02.md)，不覆盖上一版空间诊断。

**本批把“表示可压缩”与“WT→因子能否学习”分开了。**
新验证蛋白的oracle R32达到rho0.9945、Top1 30/32；两个student只有rho0.3058/0.2997、Top1 9/32与10/32，
接近WT z基线0.3009、10/32。当前配置没有形成有用的mutant pair-response替代。
这不是空间低秩假设重新失败，也不是完整C4输入信息不够或所有非线性student不可行的证明。

## 数据、隔离和交付范围

用户明确选择“新蛋白小规模pilot”。从历史folding TRAIN池中，按序列、长度、accession与冻结hash顺序选24条新response任务蛋白，
长度82–191，每条两个位点、每位点19个non-WT替换；16条训练、8条验证。
不使用旧10蛋白/50位点更新参数。旧面板继续是开发/stress资产，本批没有再对它训练。

候选池201条，加旧rank面板构建BLAST数据库；复用既有near/domain HSP排除规则，并与共享SIFTS accession一起构成连通组。
排除旧面板所在组，只从每个剩余组取一个父序列；24条来自24个组，训练/验证间无规则内同组或共享accession。
独立审计重读所有HSP并核对分组。分组是操作性序列隔离，不证明无远缘同源。
这些源蛋白曾属于历史folding资产，不能称为所有项目历史未见或Mini/ESM预训练未见。

验证8条为6AHP、1X8D、2EBE、3SXZ、4PQL、6ZRW、1YSB、2FKZ。
完整序列、位点、构建体来源、assembly背景和分组证据保存在selection.json。
没有按本轮模型质量、响应大小或训练结果删除样本。

936个不同hard序列：24WT＋912mutant。每条WT重复一次，合计960次原生ESM/C4、3840recycle。
重新计算目标ESM、原生特征/参考化学/原子图，归档完整s_inputs/s/z及两枚固定噪声230201/230211的S1坐标。
**teacher是公开Mini输出，不是实验mutant结构，也不是经化学认证的干净标签。**
实验parent的CA距离Huber目标仅用于检验原模型AA排序是否保留。

验证蛋白未进入student梯度更新；两枚噪声与训练相同。因此本批检验跨蛋白迁移，不是新蛋白＋新噪声的联合独立确认。

## Student实际实现

1,598,592个参数，width128、两层全局node attention、四个heads。
输入只有WT s/z、突变位置、WT AA与离散candidate AA。节点输入含WT single、突变row/column、全局pair均值、位置偏移和AA query；
完整WT z提供attention bias。每个candidate生成各channel独立的U/V[L,128,32]，再展开Delta z。
20AA query可以一起batch；共享生成网络没有强制所有channel使用同一组R维空间基。

**target s只在冻结decoder处作为oracle输入，绝未进入predictor forward。**
WT s_inputs、真实target chemistry及身份绑定噪声保留。没有Delta s predictor，也没有完整WT-only20AA折叠器。

监督比较重建Delta z，不直接拟合SVD U/V，避免因子符号、缩放和基变换不唯一性。
V输出投影零初始化、U随机初始化，WT query严格零响应；预检证实V有非零梯度。
两个独立初始化，runner初始化之后重新设置seed，使用相同曝光计划。
每次1024更新、前256次latent warmup、后768次加入冻结S1坐标、CA距离、clash与chirality反馈。
Mini/ESM/C4/S1权重未训练；无validation checkpoint选择、无结果驱动追加更新。

训练每步一个候选，按parent/site/AA/noise均匀采样。潜在608个训练mutant中，各次实际曝光500个不同端点；
这不是充分训练所有端点，也不是已建立数据或优化收敛的实验。
几何项是软惩罚，未承诺保持每个几何条件。

## 8条验证蛋白的主要结果

16位点×2噪声=32个AA排序；304mutant×2噪声=608份结构，不能当作608条独立蛋白。
Exact为target s_inputs/s/z；Baseline为WT s_inputs＋target s/z。
下表排序及局部偏移相对Exact；新增几何失败相对Baseline。

|方法|Delta-z归一化MSE|19-AA rho|Top1 /32|平均regret|局部均值 Å|>1Å /608|新增几何失败|
|---|---:|---:|---:|---:|---:|---:|---:|
|未压缩Baseline|0|0.999671|32|0|0.0048|0|0|
|WT z＋oracle s|1|0.300877|10|0.256189|0.8761|165|40|
|Oracle R32＋oracle s|0.0640|0.994518|30|0.000021|0.0439|0|13|
|Student seed230301＋oracle s|1.0017|0.305811|9|0.341726|0.8794|168|42|
|Student seed230303＋oracle s|0.9984|0.299726|10|0.249414|0.8745|165|42|

两个student的归一化Delta-z误差都接近“直接不预测变化”的1.0，明显远离oracle约0.064。
相对WT z的rho变化分别为+0.00493和−0.00115；8蛋白配对bootstrap95%区间分别为
[−0.02950,+0.04397]和[−0.01228,+0.01310]，没有建立直接排序优势。
每个位点两噪声均选对的数量：WT z 3/16，oracle14/16，student2/16和3/16。

第一seed的平均regret反而更大，增量主要来自6ZRW；第二seed的小幅regret改善也主要来自同一蛋白。
不能将一个平均收益或两种seed择优描述成稳健优越性。所有seed/噪声结果均保留。

新验证数据的oracle结果是正面证据：空间R32表示本身仍保留了很高的模型响应保真度。
但oracle也有13个新增几何失败；不能由高rho和0个>1Å尾部宣称完全安全。

## 不是只有验证失败：训练探针也没有接近oracle

预先hash选定4条训练蛋白、8位点、16个排序作为拟合探针，不将其视为独立验证。

|方法|Delta-z归一化MSE|rho|Top1 /16|局部>1Å /304|
|---|---:|---:|---:|---:|
|WT z|1.0000|0.422807|5|52|
|Oracle R32|0.0474|0.995285|15|0|
|Student seed230301|1.0553|0.484649|5|48|
|Student seed230303|0.9758|0.443531|5|48|

有部分局部指标改善，但没有接近teacher响应，更没有训练排序Top1的改善。
训练曝光中，前64步latent loss均值约1.0，最后128步为0.9838/0.9763；这与训练探针的有限拟合相容。
曝光均值与固定probe使用不同样本，不能要求两者数值相同。

因此当前更直接的描述是：**这个网络、损失与小预算没有充分学到有限hard response映射**。
不能简单归为过拟合，也不能从本批指定唯一原因是容量、特征、学习率、数据量或几何loss竞争。
本批没有建立这些原因的干预对照；不重新打开已收口的backward排错。

## 几何及效率限定

Baseline几何联合通过360/608；WT z为362/608，两个student都为357/608。
student各有39个原失败变通过、42个原通过变失败，净值不代表没有几何破坏。
本检查仅覆盖零严重碰撞和指定手性中心，未用旧理想化连接窗口作为唯一否决条件。
两个student最坏局部偏移仍约6.16/6.14Å；这不是oracle R32的0.589Å级别。

20AA因子生成的同步计时中位数约3.37ms、均值19.48ms、最大107.49ms，包含不同长度和首次执行差异；
逐候选展开19个non-WT的累计中位数约4.34ms。
这些是已加载WT状态后的条件模块计时，不含WT ESM/C4、target特征、oracle target s取得过程和全部S1评估。
批量与单候选展开最大差7.6294e−5，在预设1e−4 guard内，不能称逐位一致。
**小网络运行便宜与它生成正确响应是两回事；本批不能宣称实现了有用的端到端加速。**

teacher导出214.74秒；两个初始化并行训练阶段315.01秒；eval GPU315.02秒，CPU评分50.01秒。
包含准备、预检、训练及评估的student控制器742.53秒；此数不含前序teacher生成或R24诊断。
训练峰值PyTorch分配量约1.58GB，网络以外decoder被冻结；这不是完整ESM＋C4训练或设计循环显存。

## 审计与交付

- 原生WT两次C4重放一致；全部新hard输入、teacher、代码、模型权重hash保留。
- 预检同状态Baseline逐位重放、非零因子梯度、有限loss/grad通过；14项相关单元测试通过。
- 独立审计确认24个序列组隔离、无validation训练曝光，两seed各1024次相同样本计划、最终checkpoint不同且hash一致。
- 两次训练各784次S1（768更新＋16parent replay），0C4；终点评估5496次S1、0C4。
- 468个评估坐标包、924组teacher参照数组逐位一致；288项独立lDDT、960项排序检查一致。
- [机器可读结果](../reports/mini_factor_student_pilot_2026-10-02/evaluation/summary.json)、
  [逐位点排序](../reports/mini_factor_student_pilot_2026-10-02/ranking_per_site.csv)、
  [独立审计](../reports/mini_factor_student_pilot_2026-10-02/independent_audit.json)和全部失败已保存。

936份新完整conditioning约9.660GB保留远端；两份约6.4MB的student checkpoint均保留，本机也有副本，未晋升。
本机报告/坐标/checkpoint：`/home/husrcf/Code/onestepfold_runtime/factor_student_pilot_v1_20261002`。
远端：`pc@10.120.16.9:/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/factor_student_pilot_v1_20261002`。
[存储清单](../reports/mini_factor_student_pilot_2026-10-02/storage.json)记录路径、SHA和runtime源码快照范围。

## 决定

**R24补充与本次student pilot均收口。** 保留R24/R32空间因子表示、新teacher数据及两个失败student作为后续参照。
当前不把student接入设计、不给它“省20次C4”的实用加速声明，也不增加Delta s predictor来叠加另一项未知误差。
下一次若继续方法改动，应先区分当前模型的拟合能力、训练目标与数据需求；这需要新的有界协议，不能只因oracle好就无限加训练。
当前结论是“已验证可压缩表示，但尚未学出可靠生成器”，不是“这个方向已彻底不可解”。
