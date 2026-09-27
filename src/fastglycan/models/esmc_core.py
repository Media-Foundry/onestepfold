"""Fresh ESMC-conditioned all-atom core; never constructs an inference runner."""

from __future__ import annotations

import copy
import random
import time

import numpy as np
import torch
import torch.utils.checkpoint
from torch import nn

from fastglycan.decoder_gradients import detached_tree


def esmc_core_config():
    """Resolve the declared Mini topology without loading any folding weights."""
    from configs.configs_base import configs as base
    from configs.configs_data import data_configs
    from configs.configs_inference import inference_configs
    from configs.configs_model_type import model_configs
    from ml_collections import ConfigDict
    from protenix.config.config import parse_configs

    config = parse_configs(copy.deepcopy({**base, "data": data_configs, **inference_configs}),
                           fill_required_with_null=True)
    config.update(ConfigDict(copy.deepcopy(model_configs["protenix_mini_esm_v0.5.0"])))
    config.model_name = "onestepfold_esmc600m_scratch_interface_v1"
    config.load_checkpoint_dir = None
    config.esm.enable = True
    config.esm.model_name = "esmc_600m_final_cache"
    config.esm.embedding_dim = 1152
    config.model.N_cycle = 1
    config.model.N_model_seed = 1
    config.sample_diffusion.N_step = 1
    config.sample_diffusion.N_sample = 1
    config.use_msa = config.use_template = config.use_rna_msa = False
    config.mc_dropout_apply_rate = 0.0
    config.triangle_multiplicative = config.triangle_attention = "torch"
    config.enable_diffusion_shared_vars_cache = True
    config.enable_efficient_fusion = True
    config.enable_tf32 = False
    config.dtype = "bf16"
    return config


class ESMCFoldCore(nn.Module):
    """One-cycle, one-native-step core plus the standard confidence head.

    ESMC features and chemical input tensors are external frozen inputs. The
    whole folding core is freshly initialized and trainable. ``train()`` is
    required for the upstream Protenix trunk's differentiable execution path.
    """

    def __init__(self, *, seed=101, deterministic_capacity=False):
        super().__init__()
        from protenix.model.protenix import Protenix

        self.config = esmc_core_config()
        self.deterministic_capacity = deterministic_capacity
        if deterministic_capacity:
            # A bounded memorization gate, not the generalization configuration.
            self.config.model_name = "onestepfold_esmc600m_capacity_v1"
            self.config.model.pairformer.dropout = 0.0
            self.config.model.msa_module.msa_dropout = 0.0
            self.config.model.msa_module.pair_dropout = 0.0
            self.config.model.template_embedder.dropout = 0.0
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        # Protenix trunc_normal_init_ samples through SciPy's NumPy RNG.
        # Seeding torch alone does not reproduce a fresh initialization.
        numpy_state, python_state = np.random.get_state(), random.getstate()
        try:
            with torch.random.fork_rng(devices=[]):
                torch.manual_seed(seed)
                np.random.seed(seed)
                random.seed(seed)
                self.core = Protenix(self.config)
        finally:
            np.random.set_state(numpy_state)
            random.setstate(python_state)
        if tuple(self.core.input_embedder.linear_esm.weight.shape) != (449, 1152):
            raise ValueError("unexpected ESMC projection shape")

    def forward(self, features, *, confidence=True):
        from protenix.model.protenix import update_input_feature_dict

        device = next(self.parameters()).device
        if device.type != "cuda":
            raise ValueError("core execution is validated on CUDA; CPU construction is supported")
        embedding = features["esm_token_embedding"]
        if embedding.ndim != 2 or embedding.shape[-1] != 1152 or embedding.requires_grad:
            raise ValueError("expected frozen residue-aligned ESMC-600M inputs")
        if torch.is_grad_enabled() and not self.training:
            raise ValueError("use train() for trunk gradients or no_grad() for evaluation")
        inputs = detached_tree(features, device)
        inputs = self.core.relative_position_encoding.generate_relp(inputs)
        inputs = update_input_feature_dict(inputs)
        torch.cuda.synchronize(device)
        started = time.perf_counter()
        with torch.autocast("cuda", dtype=torch.bfloat16):
            s_inputs, s, z = self.core.get_pairformer_output(
                inputs, N_cycle=1, inplace_safe=False,
                chunk_size=None if self.training or self.deterministic_capacity else 4,
                mc_dropout=False)
        torch.cuda.synchronize(device)
        trunk_finished = time.perf_counter()
        module = self.core.diffusion_module
        with torch.autocast("cuda", enabled=False):
            pair_z = module.diffusion_conditioning.prepare_cache(inputs["relp"], z, False)
            names = ("ref_pos", "ref_charge", "ref_mask", "ref_element", "ref_atom_name_chars",
                     "atom_to_token_idx", "d_lm", "v_lm", "pad_info")
            p_lm, c_l = module.atom_attention_encoder.prepare_cache(
                **{k: inputs[k] for k in names}, r_l=True, z=pair_z, inplace_safe=False)
            schedule = self.core.inference_noise_scheduler(
                N_step=1, device=device, dtype=s_inputs.dtype)
            coordinate = self.core.sample_diffusion(
                denoise_net=module, input_feature_dict=inputs, s_inputs=s_inputs,
                s_trunk=s, z_trunk=None, pair_z=pair_z, p_lm=p_lm, c_l=c_l,
                N_sample=1, noise_schedule=schedule, inplace_safe=False,
                enable_efficient_fusion=self.config.enable_efficient_fusion)
        torch.cuda.synchronize(device)
        structure_finished = time.perf_counter()
        result = {"coordinate": coordinate}
        if confidence:
            with torch.autocast("cuda", dtype=torch.bfloat16):
                values = self.core.run_confidence_head(
                    input_feature_dict=inputs, s_inputs=s_inputs, s_trunk=s, z_trunk=z,
                    pair_mask=None, x_pred_coords=coordinate,
                    triangle_multiplicative="torch", triangle_attention="torch",
                    inplace_safe=False, chunk_size=4)
            result.update(zip(("plddt", "pae", "pde", "resolved"), values, strict=True))
        torch.cuda.synchronize(device)
        finished = time.perf_counter()
        result["timing"] = {
            "trunk_seconds": trunk_finished - started,
            "structure_seconds": structure_finished - trunk_finished,
            "confidence_seconds": finished - structure_finished,
            "total_core_seconds": finished - started,
        }
        return result
