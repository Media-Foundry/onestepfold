# 蛋白数据位置与组织（2026-09-29 实查）

**没有下载完整 UniProt。** 已完成的是2026-09-08 SIFTS映射涵盖的子集：
76,273个UniProt accession的FASTA序列，以及244,406个有关联映射的PDB实验结构条目。
同一accession可对应多个PDB条目和链；PDB条目数也不是独立训练序列数。

## 1. 原始下载：HPC3 与 HPC2

当前可用HPC3根目录：
`/data/user/shuang886/Folding/Dataset`

初始下载所在HPC2根目录也已确认存在：
`/hpc2hdd/home/shuang886/Folding/Dataset`

两处均看到同名目录、1,526个FASTA文件、两份对应ID清单和SIFTS三张表。
本轮在HPC3全量数了FASTA记录与PDB文件名并比对manifest；未重新进行全库gzip测试，
也未逐文件证明两台机器所有内容哈希一致。历史验收做过完整PDB gzip检查。

```text
Dataset/
├── raw/
│   ├── uniprot/2026_03/mapped_fasta/
│   │   ├── accessions.0000.fasta
│   │   ├── accessions.0001.fasta
│   │   └── ...                  # 1,526份；每批最多50条，末批23条
│   ├── pdb_mmcif/
│   │   ├── 0b/10bl.cif.gz
│   │   ├── 0b/30bu.cif.gz
│   │   └── ...                  # 按PDB ID中间两位分目录，一个条目一个文件
│   └── sifts/2026-09-08/
│       ├── pdb_chain_uniprot.csv.gz
│       ├── uniprot_pdb.csv.gz
│       └── uniprot_segments_observed.csv.gz
├── manifests/
│   ├── uniprot_accessions_with_pdb.txt  # 76,273行
│   ├── pdb_entry_ids.txt               # 244,406行
│   ├── pdb_cif_paths.list
│   ├── uniprot_batches_50/accessions.* # 与实际FASTA批次对应的accession清单
│   ├── uniprot_batches_500/            # 早期下载规划，不是另一套完整数据
│   └── pdb_entry_ids_missing_retry.txt # 历史44项重试清单，不代表现在仍缺44项
├── logs/
└── code/
```

FASTA保留UniProt标准header和序列；例如 `>sp|ACCESSION|ENTRY ...`。
`2026_03`是归档release目录标签，不能据此把该目录称为完整UniProt release镜像。
SIFTS用于entry发现、链/accession对应与残基映射；FASTA没有实验三维坐标。
PDB mmCIF则包含实验构建体、链、坐标、缺失情况等，可能多链且不是直接可训练的样本。

本轮HPC3实查：FASTA记录76,273、unique accession76,273、空记录0；accession集合
与manifest完全相等。PDB文件244,406、ID集合与manifest完全相等、`.part`残留0。
[机器可读盘点](../reports/data_inventory_2026-09-29/hpc3_raw.json)。

## 2. DiamondHill：已准备的结构训练包

`/media/PM982/onestepfold/scratch_structure_data_v1_20260927`

`acceptance.json`当前记录：complete=true，TRAIN29,769、历史DEV128，共29,897组。
统一入口为 `examples/<group_id>/`，其中部分目录是到 `new/examples/` 等子目录的软链接；
复制时注意软链接依赖，不要只复制链接而漏掉目标。

每个group的典型文件：

- `gt.npz`、`gt.json`：结构来源的GT和元数据。
- `labels.npz`、`inventory.npz`：原子/残基标签、掩码和顺序。
- `inputs.pt`、`supervision.pt`：已构建的模型输入和监督数据。
- `reference.npz`、`articulation_report.json`：化学参考/几何构建资产，**不是实验GT**。
- `prepared.json`、`input_provenance.json`：准备状态、来源与文件哈希。

训练序列由PDB实验构建体定义，保留未观测序列位置及坐标mask；不是把UniProt全长序列
硬配到截短PDB结构。29,769组是冻结选择规则后的完整序列去重TRAIN集合，不能等同于
76,273个UniProt accession。更大的DEV-primary准备与历史DEV128状态也不能混同。

另有 `/media/PM982/onestepfold/scratch_structure_inputs_v1_20260927`，其验收记录是
旧的8,192 TRAIN+128 DEV输入资产，不是29.7k主入口。
HPC3扩展结构资产还在 `/data/user/shuang886/Folding/esmc_expansion_data_v1_20260927`。
本轮检查目录/验收文件及一个包的布局，没有再次全量哈希审计29,897个包。

## 3. DiamondHill：ESMC多层缓存

`/media/PM982/onestepfold/data/esmc_29769_layers_12_24_36_v1_20260927`

```text
feature_spec.json
selection_report.json
groups.jsonl.gz
manifest.jsonl.gz
transfer_acceptance.json
part-000/shard-*.safetensors
part-001/shard-*.safetensors
part-002/shard-*.safetensors
```

验收记录：29,769组、547个shard、8,830,652个残基；ESMC-600M第12/24/36层，BF16。
`group_id`/`sequence_sha256`关联结构序列；manifest记录相对shard路径、SHA256、
`offset_start/end`、长度和层名。特征沿残基轴拼入shard，读取时按该条索引切片，
不是每蛋白一个完整模型文件。最后层原有缓存是另一个资产，不要把此三层缓存与其混称。

原提取工作目录仍有历史记录：X570 `/home/husrcf/Code/onestepfold_runtime/esmc_29769`，
Precision `/media/990Pro/onestepfold/esmc_29769_20260927`。本轮未重新连接Precision核对；
后续使用优先读本次已确认存在且有验收记录的DiamondHill统一目录。

没有在本次盘点中下载新数据、重提特征或改变任何数据划分。
