# DiamondHill ESMC transfer

Destination: `/media/PM982/onestepfold/data/esmc_29769_layers_12_24_36_v1_20260927`.

Three completed extraction partitions are copied concurrently, without deletion
of source files: X570 sends part-000; Precision directly sends part-001/002.
Rsync partial files are retained for an interrupted transfer. `transfer_jobs.json`
records the process IDs and exact commands. `transfer_exit.json` records exit
codes. Once all three transfers succeed, the controller invokes
`verify_esmc_29769_transfer.py` on DiamondHill CPU, then writes
`verification_exit.json` locally.

Only `transfer_acceptance.json` on the destination indicates successful complete
transfer verification. The verifier checks all547 shard SHA256 values, BF16 tensor
shapes/finiteness, residue offsets, source/input identity, disjoint partitions
and exact29769-group coverage. It writes root `manifest.jsonl.gz` with relative
`part-NNN/shard-*.safetensors` paths and the shared `feature_spec.json`.

This dataset contains layers12/24/36; the existing final-only cache is separate.
Cross-hardware numerical compatibility and full long-chain structure-packet
acceptance are still pending. No training is launched by this controller.
