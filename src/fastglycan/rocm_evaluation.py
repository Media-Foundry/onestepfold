"""Fixed matched-backend evaluation; historical CUDA results are not controls."""
import copy
from .folding_parameter_evaluation import make_parameter_evaluation_lock
from .evaluation_reuse import expected_evaluation_calls


def make_rocm_evaluation_lock(prior, *, train, checkpoints, training_locks,
                              selected_names, hashes, input_hashes, protocol_sha256):
    if set(checkpoints) != {'weak', 'strong'} or set(training_locks) != set(checkpoints):
        raise ValueError('both matched terminal checkpoints required')
    # Reuse the audited 455-protein/cohort/noise/assignment validation.
    out = make_parameter_evaluation_lock(prior, train=train, reference_evaluation='historical_only',
        checkpoint=checkpoints['weak'], training_lock_sha256=training_locks['weak'],
        selected_names=selected_names, hashes=hashes, input_hashes=input_hashes,
        protocol_sha256=protocol_sha256)
    out.update(schema='folding_rocm_pair_evaluation_v1', models=['weak', 'strong'],
        checkpoints=copy.deepcopy(checkpoints), checkpoint_training_locks=dict(training_locks),
        checkpoint_arms={a: 'expanded' for a in checkpoints},
        selected_names={a: list(selected_names) for a in checkpoints}, reuse_models={},
        contrasts=[['strong', 'weak']], planned_outputs=1820, planned_prediction_nfe=1820,
        planned_probe_nfe=56, primary='strong minus weak, same ROCm platform; observed DEV32 is development',
        report_title='# C4/S1 matched ROCm global-distance weight comparison',
        report_intro='Same retained512 parent, TRAIN423, ordered 8192 exposures, 2048 updates and ROCm backend. '
        'Only global-distance weight differs: weak 0.0329065568, strong 0.1810138829. '
        'Frozen ESM2/C4, native FP32 diffusion, C4/S1/K1. Experimental GT is the quality reference; '
        'cached S2 supervision is a model prediction, not experimental truth.',
        training_curve_note='Identical original-TRAIN32 inputs and initial predictions; no checkpoint selection.')
    if expected_evaluation_calls(out, out['rows']) != {'native': 0, 'weak': 910, 'strong': 910}:
        raise ValueError('matched inference budget drift')
    return out
