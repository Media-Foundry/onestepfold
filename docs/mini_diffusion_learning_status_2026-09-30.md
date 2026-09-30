# 原生一步 diffusion：缓存完成，两臂训练启动

2026-09-30。本报告记录执行与工程检查，**尚无训练终点、验证收益或部署结论**。
依据 [锁定协议](mini_diffusion_learning_pilot_v1.md) 和
[128 TRAIN＋32 VALIDATION 来源审计](mini_diffusion_training_sources_findings_2026-09-30.md)。

## 已完成

DiamondHill八个GCD并行生成160份原生FP32 C4 conditioning；仅128条TRAIN生成
两枚固定噪声下的S1/S2坐标，共512份。32条VALIDATION只有conditioning，没有预测、
教师标签或训练监督缓存。模型与数据角色未改变，ESMC缓存未用于替代原生ESM2。

| 项目 | 实测 |
|---|---:|
| 八worker结果 | 全部exit0 |
| 总墙钟 | 141.204 s |
| Pairformer stack调用 | 640 |
| diffusion调用（含训练缓存重放） | 896 |
| 训练蛋白保存/重载S1精确重放 | 128/128 |
| 工件字节数 | 28,638,960,976 |
| 单卡最高allocated显存 | 42.983 GiB |
| CPU全产物审计时间 | 63.843 s |

CPU审计读取所有缓存、坐标与哈希，核对原子数量、角色、有限性、FP32、GT mask、
观测距离、smooth-lDDT逐原子归约权重和键距离。268,933个观测训练原子用于GT监督；
560个缺失原子不进入GT距离或对齐，但仍进入预测化学约束。GPU重放证据来自各worker，
CPU审计没有重新进行GPU推理。9项loss/mask测试通过。

完整conditioning与监督缓存留在远端。仓库保留820文件的12,712,768字节证据包，
包括512份参考坐标、各目标报告、代码、协议与运行锁；每成员SHA已核验。
包SHA256：`8c9b1ea75c66c0a4fe4701aadb17830b60935dbb377f0a41b48fda0dc912ff92`。

## 正在执行

两个训练臂从同一公开Mini权重和零输出rank8适配器重新开始，并行占用GCD0/1：

- `gt`：观测GT对齐坐标、smooth-lDDT、观测键距离，以及全库存手性/碰撞监督。
- `gt_s2`：相同目标和预算，增加冻结S2坐标辅助；S2不是实验真值或化学合格标签。

每臂128条×16遍=2048次蛋白曝光，累积batch4，共512次AdamW更新。权重、顺序、
噪声、学习率和终点均预先固定；每32次更新保存恢复检查点，但只评价512终点。
训练时不读取验证数据，不以训练曲线调整预算。两臂完成并冻结后才生成验证预测。

启动控制器PID280268，GT PID280275，GT+S2 PID280276。启动检查中两臂已经完成
首个更新，零适配器S1与缓存精确一致，梯度及损失有限。PID仅为启动记录，后续状态
以远端`execution.json`和各臂`report.json`为准；本报告不把未完成作业记为成功。

## 评价与限制

旧`joint_pass`继续作为历史诊断。新损失没有强迫输出满足旧omega/连接角最大窗口；
键长度GT监督只使用真实观测值，没有因此豁免真实碰撞、错误手性或结构精度损失。
化学损失是优化引导，不能当作保证；当前权重是明确的pilot选择，并非校准最优值。

缓存冻结conditioning适用于冻结trunk的参数训练；不能用它代替设计时的实时ESM、
四轮recycle和完整序列梯度。最终仍为C4/S1，LoRA可合并回原矩阵；本轮尚未证明
适配后化学、泛化或离散设计效用。128条是首个有界试验，不是最终训练规模。

远端：

```text
/media/PM982/onestepfold/diffusion_learning_cache_v1_20260930
/media/PM982/onestepfold/diffusion_learning_pilot_v1_20260930
```

本地证据：`reports/mini_diffusion_learning_2026-09-30/`。
下一项：完成固定两臂预算、核验基础参数未变与终点重放，再按锁定规则比较32条新验证
的GT精度、退化尾部和化学指标；不恢复旧Y38搜索或FD逐段排错。
