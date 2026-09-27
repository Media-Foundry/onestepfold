"""Shared, unchanged-coordinate objective and optimizer for pretrained GT adaptation."""
import hashlib
import torch

from fastglycan.distance_supervision import observed_distance_mse
from fastglycan.experimental_training import observed_aligned_mse
from fastglycan.frame_supervision import local_frame_mse


def gt_loss_parts(coordinate, labels, supervision):
    device=coordinate.device
    return [observed_aligned_mse(coordinate,labels['coordinate'].to(device),labels['coordinate_mask'].to(device)),
            .1*local_frame_mse(coordinate,supervision['frame']),
            local_frame_mse(coordinate,supervision['same']),
            10*observed_distance_mse(coordinate,supervision['distance'])]


def configure_gt_optimizer(model):
    for module in (model.core.confidence_head,model.core.distogram_head):
        module.requires_grad_(False)
    bridge=[];core=[]
    for name,parameter in model.named_parameters():
        if parameter.requires_grad:
            (bridge if name.startswith('core.input_embedder.linear_esm.') else core).append(parameter)
    assert len(bridge)==2 and len(core)>0
    optimizer=torch.optim.AdamW([
        {'params':bridge,'lr':1e-4,'name':'esmc_projection'},
        {'params':core,'lr':1e-5,'name':'folding_core'}],
        betas=(.9,.999),eps=1e-8,weight_decay=1e-4,foreach=True)
    return optimizer


def gt_epoch_batches(records, epoch, seed=101, batch_size=4):
    """Visit every protein once, with length grouping inside shuffled pools of 64."""
    if epoch < 1 or len(records) % batch_size or batch_size != 4:
        raise ValueError('Expected complete four-protein batches and positive epoch')
    if len({r['group_id'] for r in records}) != len(records):
        raise ValueError('Duplicate sequence group')
    def key(group, kind):
        return hashlib.sha256(f'pretrained-gt-v1:{seed}:{epoch}:{kind}:{group}'.encode()).hexdigest()
    shuffled=sorted(records,key=lambda r:key(r['group_id'],'protein'))
    batches=[]
    for start in range(0,len(shuffled),64):
        pool=sorted(shuffled[start:start+64],key=lambda r:(len(r['sequence']),r['group_id']))
        batches.extend(pool[i:i+batch_size] for i in range(0,len(pool),batch_size))
    return sorted(batches,key=lambda b:key(':'.join(r['group_id'] for r in b),'batch'))
