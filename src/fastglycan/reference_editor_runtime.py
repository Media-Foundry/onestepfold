"""Native Mini/S1 runtime with reference-only editor inputs and bounded GPU cache."""
import json
from collections import OrderedDict
from pathlib import Path

import numpy as np
import torch

from fastglycan import stage0_confirm_runtime as rt
from fastglycan.adapter_supervision import build_adapter_supervision
from fastglycan.factor_student_data import FactorTeacherStore
from fastglycan.functional_response_rank import pack_conditioning
from fastglycan.hip_device_policy import guarded_hip_runtime
from fastglycan.hybrid_proposals import identity_noise
from fastglycan.models.differentiable_mini import prepare_atom_pairs, diffusion_from_conditioning
from fastglycan.models.soft_sequence_chart import native_sequence_features, device_tree
from fastglycan.paired_teacher_protocol import sha256
from fastglycan.reference_editor_multiref import validate_multiref_plan


class MiniEditorRuntime:
    def __init__(self, root, work_name, building=False):
        self.root = Path(root)
        self.runtime = guarded_hip_runtime()
        self.lock = rt.load_json(self.root / 'lock.json')
        self.check_code()
        self.plan = rt.load_json(self.root / 'plan.json')
        assert sha256(self.root / 'plan.json') == self.lock['plan_sha256']
        self.sites = validate_multiref_plan(self.plan)
        self.store = FactorTeacherStore(self.lock['teachers'])
        for name, digest in self.plan['teacher_metadata_hashes'].items():
            assert sha256(self.store.root / name) == digest, name
        for path, digest in self.store.lock['weights_sha256'].items():
            assert sha256(Path(path)) == digest, path
        runner = rt.runner_setup(self.root / work_name)
        runner.configs.dtype = 'fp32'
        assert runner.configs.model_name == 'protenix_mini_esm_v0.5.0'
        self.decoder = runner.model.eval().requires_grad_(False)
        self.counts = dict(c4=0, input_embedder=0, s1=0, updates=0)
        self.handles = [
            self.decoder.pairformer_stack.register_forward_pre_hook(self.forbid_trunk),
            self.decoder.input_embedder.register_forward_pre_hook(self.forbid_inputs),
            self.decoder.diffusion_module.register_forward_hook(self.count_decode),
        ]
        self.aa = self.store.lock['aa']
        self.noises = self.store.lock['seeds']
        assert self.noises == [230201, 230211]
        self.references = {}
        self.sequences = {}
        for parent in self.plan['parents']:
            pi = parent['parent_index']
            source = self.store.load(pi)  # Only WT conditioning is persistently loaded.
            self.references[pi] = tuple(t.cuda() for t in source['conditioning'])
            self.sequences[pi] = tuple(self.aa.index(a) for a in source['sequence'])
        self.cpu_packets = {}
        self.gpu_packets = OrderedDict()
        self.building = building
        self.packet_manifest = {} if building else rt.load_json(self.root / 'packet_manifest.json')
        if not building:
            preflight = rt.load_json(self.root / 'preflight.json')
            assert preflight['complete']
            assert sha256(self.root / 'packet_manifest.json') == preflight['packet_manifest_sha256']

    def check_code(self):
        for path, digest in self.lock['code'].items():
            assert sha256(self.root / 'code' / path) == digest, path

    def forbid_trunk(self, *args):
        self.counts['c4'] += 1
        raise AssertionError('C4 forbidden: archived reference memory only')

    def forbid_inputs(self, *args):
        self.counts['input_embedder'] += 1
        raise AssertionError('target input encoder/ESM forbidden')

    def count_decode(self, *args):
        self.counts['s1'] += 1

    def edits(self, site, choices):
        pos = site['position_zero_based']
        old = self.aa.index(site['original_aa'])
        return [[(pos, old, self.aa.index(a))] for a in choices]

    def label(self, parent, position=None, aa=None):
        return f'p{parent}_wt' if position is None else f'p{parent}_s{position+1}_{aa}'

    def build_packet(self, parent, position=None, aa=None):
        if not self.building:
            raise RuntimeError('native packet preparation is preflight-only')
        sequence = self.store.rows[parent]['sequence']
        if position is not None:
            sequence = sequence[:position] + aa + sequence[position+1:]
        label = self.label(parent, position, aa)
        inv = dict(np.load(self.store.path(parent, label, 'inventory.npz')))
        co = np.load(self.store.path(parent, label, 'coordinates.npz'))['coordinates']
        exact = co if position is None else co[0]
        native, atoms = native_sequence_features(sequence)
        assert np.array_equal(atoms.atom_name, inv['atom_names'])
        assert np.array_equal(atoms.bonds.as_array(), inv['bonds'])
        assert np.array_equal(native['ref_pos'].numpy(), inv['reference'])
        features = prepare_atom_pairs(self.decoder.relative_position_encoding.generate_relp(device_tree(native, 'cuda')))
        labels = build_adapter_supervision(
            dict(inv, coordinates=exact[0], mask=np.ones(len(atoms), bool)), inv['bonds'], sequence)
        packet = dict(label=label, parent=parent, position=position, aa=aa,
                      features=device_tree(features, 'cpu'),
                      noises=[identity_noise(atoms, n, device='cpu') for n in self.noises],
                      teacher=torch.tensor(exact), labels=labels,
                      ca=torch.tensor(np.flatnonzero(inv['atom_names'] == 'CA')))
        # No candidate conditioning, sequence embedding or latent label in this packet.
        path = self.root / 'packets' / f'{label}.pt'
        torch.save(packet, path)
        self.packet_manifest[label] = dict(path=str(path.relative_to(self.root)), sha256=sha256(path))
        self.cpu_packets[label] = packet
        return self.item(parent, position, aa)

    def item(self, parent, position=None, aa=None):
        label = self.label(parent, position, aa)
        if label in self.gpu_packets:
            self.gpu_packets.move_to_end(label)
            return self.gpu_packets[label]
        if label not in self.cpu_packets:
            record = self.packet_manifest[label]
            path = self.root / record['path']
            assert sha256(path) == record['sha256'], label
            self.cpu_packets[label] = torch.load(path, map_location='cpu', weights_only=False)
        source = self.cpu_packets[label]
        assert set(source) == {'label', 'parent', 'position', 'aa', 'features', 'noises', 'teacher', 'labels', 'ca'}
        packet = dict(source, features=device_tree(source['features'], 'cuda'),
                      noises=[x.cuda() for x in source['noises']],
                      teacher=source['teacher'].cuda(), ca=source['ca'].cuda())
        self.gpu_packets[label] = packet
        while len(self.gpu_packets) > 8:
            self.gpu_packets.popitem(last=False)
        return packet

    def decode(self, item, conditioning, noise):
        return diffusion_from_conditioning(
            self.decoder, item['features'], item['noises'][noise],
            pack_conditioning(conditioning), steps=1).squeeze(0)

    def finish_checks(self):
        self.check_code()
        assert self.counts['c4'] == self.counts['input_embedder'] == 0
        assert all(p.grad is None for p in self.decoder.parameters())
        for path, digest in self.store.lock['weights_sha256'].items():
            assert sha256(Path(path)) == digest, path


def editor_cache_audit(net, runtime):
    """Real-shape candidate invariants; no updates, no relaxed pilot tolerance."""
    pi = 3
    raw, sequence = runtime.references[pi], runtime.sequences[pi]
    query = [[], [(36, sequence[36], 0)], [(83, sequence[83], 1)]]
    with torch.no_grad():
        ref = net.prepare_reference(raw, sequence)
        out = net(ref, query)
        fresh = net(net.prepare_reference(raw, sequence), query)
        reverse = net(ref, query[::-1])
        assert all(torch.equal(a, b) for a, b in zip(out, fresh))
        assert all(torch.equal(a[0], r) for a, r in zip(out, raw))
        error = max(float((a - b.flip(0)).abs().max()) for a, b in zip(out, reverse))
        for i, q in enumerate(query):
            alone = net(ref, [q])
            error = max(error, max(float((a[i] - b[0]).abs().max()) for a, b in zip(out, alone)))
        assert error < 1e-4, error
        item = runtime.item(pi)
        assert torch.equal(runtime.decode(item, tuple(x[0] for x in out), 0), item['teacher'][0])
    return dict(cache_fresh_bitwise=True, noedit_bitwise=True, order_subset_max=error)


def gradient_inventory(net, architecture):
    """Distinguish disconnected parameters from zero current-batch gradients."""
    required = ['inputs.1.weight', 'aa.weight', 'pair_base.1.weight',
                'input_out.weight', 'single_out.weight', 'pair_out.3.weight']
    required.append('blocks.0.read.q.weight' if architecture == 'workspace' else 'node_blocks.0.1.weight')
    norms = {}
    disconnected, zero = [], []
    registered = connected = nonzero = 0
    for name, p in net.named_parameters():
        registered += p.numel()
        if p.grad is None:
            disconnected.append(name)
            continue
        assert torch.isfinite(p.grad).all(), name
        connected += p.numel()
        norm = float(p.grad.norm())
        norms[name] = norm
        if norm:
            nonzero += p.numel()
        else:
            zero.append(name)
    assert all(norms.get(name, 0) > 0 for name in required), {k: norms.get(k) for k in required}
    return dict(registered=registered, gradient_connected=connected,
                nonzero_gradient_parameters=nonzero, disconnected=disconnected,
                zero_gradient_names=zero, required_norms={k: norms[k] for k in required})
