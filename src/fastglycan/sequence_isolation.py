"""Auditable HSP-based isolation, distinct from global aligned-column identity."""
from dataclasses import dataclass


@dataclass(frozen=True)
class HSP:
    query: str
    subject: str
    query_length: int
    subject_length: int
    evalue: float
    query_aligned: str
    subject_aligned: str

    def evidence(self):
        if len(self.query_aligned) != len(self.subject_aligned):
            raise ValueError('unequal aligned strings')
        if min(self.query_length, self.subject_length) <= 0 or self.evalue < 0:
            raise ValueError('invalid lengths or E-value')
        columns = [(q, s) for q, s in zip(self.query_aligned, self.subject_aligned) if q != '-' and s != '-']
        n = len(columns)
        if n > min(self.query_length, self.subject_length):
            raise ValueError('alignment exceeds sequence length')
        identity = sum(q == s for q, s in columns)/n if n else 0.
        coverage = n/min(self.query_length, self.subject_length)
        near = n >= 50 and identity >= .30 and coverage >= .70 and self.evalue <= .001
        domain = n >= 50 and self.evalue <= 1e-5
        return dict(aligned_residues=n, identity=identity, shorter_coverage=coverage,
                    evalue=self.evalue, near=near, domain=domain, excluded=near or domain)


def read_hsps(path):
    """Read explicit outfmt: qseqid sseqid qlen slen evalue qseq sseq."""
    with open(path) as handle:
        for line in handle:
            if not line.strip() or line.startswith('#'):
                continue
            q, s, ql, sl, e, qa, sa = line.rstrip().split('\t')
            yield HSP(q, s, int(ql), int(sl), float(e), qa, sa)
