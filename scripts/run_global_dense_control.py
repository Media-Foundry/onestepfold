"""Correction of the row-wise dense diagnostic; same bounded training loop."""
import argparse,time
from pathlib import Path
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.paired_teacher_protocol import write_json
from fastglycan.factor_student_data import FactorTeacherStore
from fastglycan.deep_dense_control import GlobalDenseControl
from fastglycan.factor_memorization import response_nmse
import run_deep_validation_v2 as training


def preflight_global_dense(root):
    runtime=training.gpu_guard();lock=rt.load_json(root/'lock.json');store=FactorTeacherStore(Path(lock['teachers']),training_only=True);d=training.site_tensors(store,3,36,oracle_floor=False);proof=[]
    for seed in [231301,231303]:
        torch.manual_seed(seed);net=GlobalDenseControl().cuda()
        with torch.no_grad():
            feature,_=net.query_features(d['s'],d['z'],d['pos'],d['wt'],d['ids']);design=torch.cat([feature.double(),torch.ones(19,1,device='cuda',dtype=torch.float64)],1);sv=torch.linalg.svdvals(design);assert torch.linalg.matrix_rank(design)==19
            coeff=torch.linalg.pinv(design)@d['target'].double().flatten(1);prediction=(design@coeff).reshape_as(d['target']);error=float(response_nmse(prediction,d['target'].double()).mean());assert error<1e-16
            net.dense.weight.copy_(coeff[:-1].T.float());net.dense.bias.copy_(coeff[-1].float());x=training.predict_site(net,d);fp32=float(response_nmse(x,d['target']).mean());assert fp32<1e-8
            proof.append(dict(seed=seed,feature_rank=19,feature_smallest_singular=float(sv[-1]),closed_form_nmse=error,fp32_readout_nmse=fp32))
        del coeff,prediction,net
    # Fresh initialization: no fitted coefficients retained or passed to jobs.
    torch.manual_seed(231301);net=GlobalDenseControl().cuda();opt=torch.optim.AdamW(net.parameters(),lr=3e-4);start=time.monotonic()
    for step in range(24):
        opt.zero_grad(set_to_none=True);loss=response_nmse(training.predict_site(net,d),d['target']).mean();loss.backward();torch.nn.utils.clip_grad_norm_(net.parameters(),1.,error_if_nonfinite=True);opt.step()
        if step==3:torch.cuda.synchronize();start=time.monotonic()
    torch.cuda.synchronize();write_json(root/'preflight.json',dict(complete=True,runtime=runtime,proof=proof,parameters=sum(p.numel() for p in net.parameters()),step_seconds=(time.monotonic()-start)/20,retained_oracle_initialization=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',choices=['preflight','train'],required=True);p.add_argument('--job');a=p.parse_args()
    if a.mode=='preflight':preflight_global_dense(a.root)
    else:
        training.DeepResponseStudent=GlobalDenseControl
        training.train_deep_job(a.root,a.job)
