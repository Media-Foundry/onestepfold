# C4/S1 参数梯度匹配权重：固定终点评估 v1

评估对象：`mini_folding_global_parameter_weight_v1` 的唯一 2048 更新终点。
这是既定训练对照的评估实现，未新增训练分支或评价样本。

## 样本、参照与预算

固定 TRAIN423（原128＋新增295）和已反复观察的 DEV32，各两枚固定噪声。
TRAIN 噪声 600001、600011；DEV 噪声 810013、810029。不选择噪声或中间 checkpoint。
DEV 仍是开发证据，不称新独立验证。

六个已完成模型：native_s1、native_s2、retained、expanded、coordinate_zero、
global_distance。新模型名 `global_parameter_matched`，序列、化学输入、C4 条件、
FP32 计算与 C4/S1/K1 推理规则不变。训练 checkpoint 内部 arm 仍是 expanded，
评估显示的模型名与 checkpoint arm 分开验证。

复用旧全局距离评估的全部 5460 份坐标，并逐份核验哈希及 worker 报告。
新增 455×2＝910 次预测，八个分片各4次工程预检，总新 NFE 为942；
七模型的最终评分分母为6370。缺失、失败或非有限输出不缩减分母。

绑定既有参考：
- 评估 lock SHA256：f89f2649e957ac4158895c62a73eb560c81c91036468c6b5591771bdbc4c8a9d。
- evaluation.json SHA256：6524194f416ef25c5a51abb5e00cf3dcc4a613f0ccd62a8816c6f36ce613acbd。

## 执行次序与放行

独立目录 `folding_global_parameter_evaluation_v1_20260930`。
先复制已完成 global_distance evaluation 的冻结 code，再追加本版脚本、模块及协议，
不从当前整个工作区覆盖远端模型代码。

1. `evaluate_folding_global_parameter.py --mode prepare`：训练审计完成后，核验唯一权重改变、
   完整初始状态与样本顺序、终点 checkpoint、旧六模型输出及实验 GT 映射；写新 lock。
2. 复用未改动的 `evaluate_diffusion_learning.py --mode worker --index 0..7` 运行八个分片。
3. `--mode collect`：核验调度器与所有分片完成，逐份精确重放训练终点的64份 TRAIN32坐标。
4. `--mode score --workers 8`：先检查上述重放证明，再调用原评分器及蛋白层级配对统计。
5. `--mode extent --workers 8`：仅用保存坐标复算全局距离与误差分布，不新增推理。
6. `--mode report`：检查评分与 extent 作业 COMPLETED 0:0，保存报告、配对表及完整来源哈希。

所有命令均须 `--root`。submission.json 使用既有收集器字段：training_jobs、audit_job、
prepare_job、worker_jobs（按分片顺序8项）、score_job、extent_job；均填实际 Slurm ID。
评分作业应顺序执行 collect 与 score，任何失败终止；extent afterok score，report afterok extent。
仅在 HPC3 acd_u 权限恢复且训练终点审计成功后提交。本协议不绕过当前分区访问限制。

## 结果解释

主要比较同时保留 candidate−global_distance 和 candidate−expanded；另报与 coordinate_zero、
retained、native_s1、native_s2 的差异。每条蛋白先平均两枚噪声，再进行蛋白 bootstrap。

保留实验 GT 的 AA/Cα-lDDT、全链 RMSD、配对 P01/P05/worst5%、退化超过0.05的蛋白，
严重碰撞、严格所检立体中心、连接残差与新引入违例。旧连接门槛只作历史诊断。
报告远距离 MAE/有符号误差、片段 RMSD、去掉最大5%残差后的 RMSD、回转半径比及实际成本。
far band 为序列间隔≥24、实验距离≥30 Å；无支持的蛋白保留 null 与有效分母。

全局距离摘要同时列两个主要比较；残差集中程度的逐蛋白主参照固定为 global_distance。
结果不自动晋升为默认模型，不声称接近 S2、化学全面有效或可用于结合设计。
推理计时只覆盖缓存 C4 条件下 diffusion，不是端到端 ESM2＋C4＋S1 速度。

## 当前实现验证范围

锁定构造已用真实归档455条清单测试，包含拒绝重复/遗漏/噪声及分组变更。
原生推理器、评分器、结构诊断器保持不变。本版尚未执行新模型推理或评分：
新训练尚因 acd_u 用户组限制未启动。实现通过测试不等于获得模型质量结果。
