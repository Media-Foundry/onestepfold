"""Streaming FP64 AA-response metrics; no rank truncation or fitted scaling."""
import math
import torch


class ResponseMoments:
    def __init__(self):
        self.n = 0
        self.sum_p = self.sum_t = None
        self.pp = self.tt = self.pt = 0.

    def add(self, predicted, target):
        p, t = predicted.detach().double(), target.detach().double()
        if p.shape != t.shape or not torch.isfinite(p).all() or not torch.isfinite(t).all():
            raise ValueError('finite matched tensors required')
        if self.n == 0:
            self.sum_p, self.sum_t = torch.zeros_like(p), torch.zeros_like(t)
        self.sum_p.add_(p); self.sum_t.add_(t)
        self.pp += float(p.square().sum())
        self.tt += float(t.square().sum())
        self.pt += float((p*t).sum())
        self.n += 1

    def result(self):
        if not self.n:
            raise ValueError('empty candidate set')
        mp = float(self.sum_p.square().sum()) / self.n
        mt = float(self.sum_t.square().sum()) / self.n
        dot = float((self.sum_p*self.sum_t).sum()) / self.n
        result = {}
        for name, pp, tt, pt in (('raw',self.pp,self.tt,self.pt),
                                ('centered',max(0.,self.pp-mp),max(0.,self.tt-mt),self.pt-dot),
                                ('common',mp,mt,dot)):
            error = max(0.,pp+tt-2*pt)
            result[name] = dict(target_energy=tt/self.n, predicted_energy=pp/self.n,
                error_energy=error/self.n, nmse=error/tt if tt>1e-24 else None,
                energy_ratio=pp/tt if tt>1e-24 else None,
                cosine=pt/math.sqrt(pp*tt) if min(pp,tt)>1e-24 else None)
        result['candidates'] = self.n
        return result
