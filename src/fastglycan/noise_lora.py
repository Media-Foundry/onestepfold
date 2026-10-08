"""Locked single/two-noise exposure, with matched decoder noise and teacher."""
import json
from collections import Counter
from pathlib import Path

from fastglycan.paired_distributed import CandidateStructureLoss
from fastglycan.paired_teacher_protocol import sha256


def noise_index_for_exposure(arm, step, rank, sites=27):
    if arm not in ('single', 'dual') or not 0 <= step < 8208 or rank not in (0, 1) or sites != 27:
        raise ValueError('outside locked noise experiment')
    # Each site's candidate stream cycles through 19 AAs. Count exposure of
    # that particular AA, not parity of update/rank (which would confound AA).
    exposure = (2 * (step // sites) + rank) // 19
    return 0 if arm == 'single' else exposure % 2


def noise_schedule_exposures(arm):
    result = Counter()
    for step in range(8208):
        for rank in (0, 1):
            result[(step % 27, (2 * (step // 27) + rank) % 19,
                    noise_index_for_exposure(arm, step, rank))] += 1
    expected = 32 if arm == 'single' else 16
    assert len(result) == 513 * (1 if arm == 'single' else 2)
    assert set(result.values()) == {expected}
    return result


def read_noise_lock(root):
    root = Path(root)
    lock = json.loads((root / 'noise_lock.json').read_text())
    assert lock['arms'] == ['single', 'dual'] and lock['seeds'] == [272001, 272003]
    assert lock['updates'] == 8208 and lock['noises'] == [230201, 230211]
    assert sha256(root / 'protocol.md') == lock['protocol_sha256']
    for path, digest in lock['code'].items():
        assert sha256(root / 'code' / path) == digest, path
    source = Path(lock['source'])
    assert sha256(source / 'lora_lock.json') == lock['source_lock_sha256']
    for seed, digest in lock['initial_checkpoints'].items():
        assert sha256(source / 'runs' / seed / 'checkpoints/0.pt') == digest
    return lock


class NoiseCandidateLoss(CandidateStructureLoss):
    """Reuse original objective; noise identity never enters conditioning."""
    def forward(self, site, aa, noise_index):
        if noise_index not in (0, 1):
            raise ValueError('only archived noise indices are allowed')
        item, conditioning = self.runtime.conditioning(self.bank, site, aa)
        x = self.runtime.base.decode(item, conditioning, noise_index)
        loss, self.last_components = self.objective(
            x, item['teacher'][noise_index], item['ca'], item['labels'])
        return loss
