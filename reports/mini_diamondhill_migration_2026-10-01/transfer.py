from pathlib import Path
import subprocess,json,time,os
r=Path(__file__).parent
cmd=['rsync','-a','--partial','--partial-dir=.rsync-partial','--info=progress2','--files-from='+str(r/'files.txt'),'hpc3:/data/user/shuang886/Folding/','/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/']
start=time.time()
with (r/'rsync.log').open('w') as log:
 p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT)
 (r/'transfer_handle.json').write_text(json.dumps(dict(controller_pid=os.getpid(),rsync_pid=p.pid,start_unix=start,command=cmd),indent=2)+'\n')
 code=p.wait()
(r/'transfer_result.json').write_text(json.dumps(dict(exit_code=code,seconds=time.time()-start,complete=code==0),indent=2)+'\n')
