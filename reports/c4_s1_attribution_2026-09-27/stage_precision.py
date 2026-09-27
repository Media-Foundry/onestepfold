from pathlib import Path
import hashlib,json,shutil
r=Path('/data/user/shuang886/Folding/c4_s1_attribution_v1_20260927')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert json.loads((r/'preflight/complete.json').read_text())['complete']
shutil.copytree(r/'code_v1',r/'code_precision_v1')
for n in ('run_c4_s1_precision.py','score_c4_s1_attribution.py'):shutil.copy2(r/n,r/'code_precision_v1/scripts'/n)
source=r/'code_precision_v1';(r/'precision_source_manifest.json').write_text(json.dumps(dict(files={str(p.relative_to(source)):sha(p) for p in source.rglob('*.py')}),indent=2)+'\n')
(r/'precision_lock.json').write_text(json.dumps(dict(locked=True,parent_lock_sha256=sha(r/'lock.json'),dtype='fp32',parameter_dtype='torch.float32',panel='B102 diagnostic only',n_predictions=1224,seeds=[103,107,109,113],N_cycle=4,steps=[1,2,5],initial_noise='Replay actual raw and first-denoiser noise tensors from controlled BF16 artifacts, exact numeric equality required',TF32='Retain historical flags: matmulFalse cuDNNTrue; CLI fp32, not all-op IEEE FP32 claim',only_change='Autocast precision with frozen weights and common actual denoiser starting coordinates',criterion='Within-setting fp32 minus bf16 quality, tail persistence and costs; no posthoc precision selection using this panel'),indent=2)+'\n')
