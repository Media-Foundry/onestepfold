"""Copy completed diagnostic evidence with hashes; coordinates stay archived."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path


def export_pair_readout(root):
    assert json.loads((root/'controller.json').read_text())['complete']
    destination=root/'export';destination.mkdir(exist_ok=False)
    files={}
    def copy(source,name):
        target=destination/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target)
        digest=hashlib.sha256(source.read_bytes()).hexdigest()
        assert hashlib.sha256(target.read_bytes()).hexdigest()==digest
        files[name]=digest
    for name in ('readout_lock.json','protocol.md','controller.json','controller.log','preflight_tests.log'):
        copy(root/name,name)
    for path in sorted(root.glob('fit_*.log'))+sorted(root.glob('score_*.log')):
        copy(path,path.name)
    for arm in ('pretrained','random'):
        for seed in (272001,272003):
            folder=Path('runs')/arm/str(seed)
            for name in ('report.json','fit.json','evaluation.json','readouts.pt','summary.json','scores.json.gz'):
                copy(root/folder/name,str(folder/name))
    failed=root.parent/'pair_readout_v1_20261009'
    for name in ('readout_lock.json','protocol.md','preflight_tests.log','preflight_tests_available.log'):
        copy(failed/name,'failed_preflight/'+name)
    for name in ('src/fastglycan/pair_readout.py','tests/test_pair_readout.py'):
        copy(failed/'code'/name,'failed_preflight/code/'+name)
    (destination/'manifest.json').write_text(json.dumps(dict(source=str(root),files=files),indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(files=len(files),bytes=sum((destination/n).stat().st_size for n in files))))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    export_pair_readout(parser.parse_args().root)
