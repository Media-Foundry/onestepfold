from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import time,json,hashlib,os,traceback
r=Path(__file__).parent;base=Path('/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding');start=time.monotonic()
(r/'verification_handle.json').write_text(json.dumps(dict(pid=os.getpid(),started_unix=time.time()))+'\n')
try:
 while not (r/'transfer_result.json').exists():
  if time.monotonic()-start>7200:raise TimeoutError('transfer result not available within two hours; no automatic restart')
  time.sleep(5)
 transfer=json.loads((r/'transfer_result.json').read_text());assert transfer['complete'] and transfer['exit_code']==0
 source=json.loads((r/'hash_manifest_report.json').read_text());manifest_path=r/'sha256_manifest.json'
 assert hashlib.sha256(manifest_path.read_bytes()).hexdigest()==source['manifest_sha256']
 manifest=json.loads(manifest_path.read_text());assert len(manifest)==24397
 def verify(item):
  name,record=item;p=base/name
  if not p.is_file() or p.stat().st_size!=record['size']:return dict(path=name,error='missing or wrong size')
  h=hashlib.sha256()
  with p.open('rb') as f:
   for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
  return None if h.hexdigest()==record['sha256'] else dict(path=name,error='hash mismatch',observed=h.hexdigest())
 with ThreadPoolExecutor(max_workers=4) as pool:failures=[x for x in pool.map(verify,manifest.items()) if x is not None]
 result=dict(complete=not failures,files=len(manifest),bytes=sum(x['size'] for x in manifest.values()),failures=failures,seconds_including_wait=time.monotonic()-start,manifest_sha256=source['manifest_sha256'],scope='transfer integrity only; model/backend preflight still required')
except Exception:result=dict(complete=False,error=traceback.format_exc(),seconds_including_wait=time.monotonic()-start)
(r/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
