"""Whole-field dense control without the candidate-times-residue row bottleneck."""
import torch
from torch import nn
from fastglycan.deep_response_student import DeepResponseStudent


class GlobalDenseControl(DeepResponseStudent):
    """Fixed-length diagnostic, not an efficient transferable pair predictor.

    32 query features suffice to span19 candidate outputs at one fixed site.
    They do not impose rank128 on the 19*L residue rows, unlike the row head.
    """
    def __init__(self,size='small',content=False,output='global_dense',length=84,
                 single_channels=384,pair_channels=128,rank=32,input_channels=449,
                 query_width=32):
        if output!='global_dense':raise ValueError('this is the whole-field diagnostic only')
        super().__init__(size=size,content=content,output='dense',length=length,single_channels=single_channels,pair_channels=pair_channels,rank=rank,input_channels=input_channels)
        width=128 if size=='small' else 256
        self.global_query=nn.Sequential(nn.LayerNorm(width),nn.Linear(width,query_width),nn.GELU())
        self.dense=nn.Linear(query_width,length*length*pair_channels);nn.init.zeros_(self.dense.weight);nn.init.zeros_(self.dense.bias)

    def query_features(self,wt_s,wt_z,position,wt_aa,candidate_aa):
        h,aa=self.node_response(wt_s,wt_z,position,wt_aa,candidate_aa)
        return self.global_query(h.mean(1)+h[:,position]),aa

    def forward(self,wt_s,wt_z,position,wt_aa,candidate_aa,wt_inputs=None,target_inputs=None):
        if len(wt_s)!=self.length:raise ValueError('fixed-length diagnostic')
        if wt_inputs is not None or target_inputs is not None:raise ValueError('WT-only features, no oracle target input')
        h,aa=self.query_features(wt_s,wt_z,position,wt_aa,candidate_aa)
        return self.dense(h).reshape(len(aa),self.length,self.length,self.pair_channels)*(aa!=wt_aa)[:,None,None,None]
