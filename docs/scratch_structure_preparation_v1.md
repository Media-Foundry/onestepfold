# 29,769 TRAIN 结构包准备（仅数据，不训练）

用户明确把当前执行范围收窄为结构准备。本轮没有启动TRAIN32、优化器更新或正式模型训练。此前写好的训练相关代码暂存，不由本流水线执行。

DiamondHill工作目录：`/media/PM982/onestepfold/scratch_structure_data_v1_20260927`。

- 完整目标：29,769 TRAIN＋128历史DEV，共29,897个包。
- 复用8,192 TRAIN＋128 DEV：从HPC3已验收数据直接rsync，按原acceptance的prepared.json哈希及各文件哈希验收，源数据不改动。
- 新建21,577 TRAIN：结构构建体序列，20–1024残基，原始mmCIF全部已确认存在。保留缺失位置与掩码，不补造坐标、不裁剪、不跳过长链。
- 首批6条长度为20、257、321、427、1022、1024，两个CPU进程已经全部成功。原始GT重建、原子名/残基映射、ESMC对齐、参考化学图、独立坐标投影及有限差分检查通过。
- 旧final-layer ESMC178分片执行完整校验和检查；新包使用同一缓存，MLC不进入本轮结构准备。
- 首批通过后自动使用16个CPU worker准备余下新包。各worker单线程，GPU显式隐藏；无需占用8个MI250 GCD。
- 新包额外保存smooth-lDDT稀疏监督及有效原子/pair计数；已有包保持原样，旧包的smooth缓存后续可独立补齐，不冒充已经完成。
- 出错不删除目标、不静默改筛选规则；完整验收只有在所有worker成功、旧包传输完成及每个文件检查通过后生成。

进度：`launch.json`、`new/progress_worker_*.json`、`reuse_transfer.log`；各阶段退出记录为`smoke/exit.json`、`new/exit.json`、`reuse_transfer_exit.json`、`pipeline_exit.json`。最终`acceptance.json`是结构包完成标志，不代表长链显存、训练吞吐或模型质量验收通过。更大的DEV-primary尚未锁定/准备。

源码：`prepare_scratch_structure_data.py`沿用已验收准备实现，只增加显式化学资产路径、已校验包复用及smooth标签；控制器和选择脚本归档在`reports/scratch_structure_data_v1_20260927`。新源码快照独立于任何已有训练作业。

## 并发更新

按用户要求已切换为192个单核绑定CPU worker，PyTorch intra/inter-op、BLAS等线程均限制为1。保留2677个完成包，16个中断包隔离后重做；新控制器位于`scale192/run.py`，原16-worker控制器已停止。校验入口改为code_v2，数据规则和目标数不变。
