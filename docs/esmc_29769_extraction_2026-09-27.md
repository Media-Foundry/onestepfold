# 29,769 条结构序列：ESMC 多层提取

用户接受约29.7k，并要求结构来源序列、本机及Precision GPU提取，启动后停止。此阶段不启动训练，也不把序列清单视为结构包验收完成。

选择29,769条完整序列去重的训练蛋白，长度20–1024，共8,830,652个残基。取消旧32–256实验限制；保留2021-09-30截止日期、既有TRAIN质量规则、20种标准氨基酸与全部1600条DEV排除。保留旧8192训练代表结构，DEV128不变。组表来自已处理结构的构建体序列，不是UniProt全长序列；未观测位置保留原序列位置，由坐标掩码处理。

选择清单SHA256：`4fd740e5fda9f709c973065a4cb6f7a620d36c8e1101ad818a96862785af4ecb`。
所有29,769条已有final-layer缓存，因此新提取只补第12/24/36层，供用户要求的MLC独立对照；当前final-only折叠实验不换输入。每个GPU还保存三个相同长度分层TRAIN启动探针的三层及final输出，供后续跨设备检查。

|设备|分区|序列数|残基数|工作目录|
|---|---:|---:|---:|---|
|X570 R9700 32GB|0|9887|2941726|`/home/husrcf/Code/onestepfold_runtime/esmc_29769`|
|Precision W7900 48GB，GPU0|1|9957|2952403|`/media/990Pro/onestepfold/esmc_29769_20260927`|
|Precision W7900 48GB，GPU1|2|9925|2936523|同上|

分区规则：序列SHA256前16位转整数后模3，无重复。冻结Biohub代码`bf343ba264b650dff7a073643725f9aaa1fdbe8d`、ESMC600M权重revision `28aed46fcaf217dfa59f78a589bb449aa3ae5d98`；每卡独立进程，batch token预算2048，BF16 safetensors，准确去除BOS/EOS。代码与输入哈希写入lock，每批进度写入progress.json；程序结束后才产生完整manifest及summary。

后续必须验证：三分区恰好覆盖全部目标、所有分片校验和/形状/有限值、跨机器探针数值及既有final缓存兼容性、layer36与final的归一化关系。不同ROCm/PyTorch运行时暂不视为完全等价，不把未经比较的多层特征直接混入正式质量对照。新增长链结构包、显存/裁剪、train–dev同源性和完整数据验收仍待处理。

最初选择脚本误用HPC3系统Python3.6，写报告时不支持dict union；部分产物保存在`esmc_29769_selection_v1_20260927_python36_partial`。改用fold Python3.12完整重跑，新清单独立冻结，失败产物不用于提取。
