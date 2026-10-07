"""Reference-only memory, isolated hard-edit workspaces and dense late writeout.

No teacher state or target encoder is accepted by the inference interface.
Persistent raw Mini memory is separate from parameter-versioned trainable caches.
"""
from dataclasses import dataclass
import math
import torch
from torch import nn


class EditAttention(nn.Module):
    def __init__(self, width, heads):
        super().__init__()
        self.width, self.heads = width, heads
        self.q = nn.Linear(width, width)
        self.kv = nn.Linear(width, 2 * width)
        self.out = nn.Linear(width, width)

    def project_memory(self, memory):
        k, v = self.kv(memory).chunk(2, -1)
        return tuple(t.reshape(*t.shape[:-1], self.heads, self.width // self.heads).transpose(-3, -2) for t in (k, v))

    def forward(self, query, kv):
        q = self.q(query).reshape(*query.shape[:-1], self.heads, self.width // self.heads).transpose(-3, -2)
        k, v = kv
        weights = torch.softmax((q @ k.transpose(-1, -2)) / math.sqrt(self.width // self.heads), -1)
        return self.out((weights @ v).transpose(-3, -2).reshape(query.shape))


class EditWorkspaceBlock(nn.Module):
    def __init__(self, width, heads):
        super().__init__()
        self.read = EditAttention(width, heads)
        self.feedback = EditAttention(width, heads)
        self.interact = EditAttention(width, heads)
        self.write = EditAttention(width, heads)
        self.norms = nn.ModuleList([nn.LayerNorm(width) for _ in range(6)])
        self.work_ff = nn.Sequential(nn.LayerNorm(width), nn.Linear(width, 4 * width), nn.SiLU(), nn.Linear(4 * width, width))
        self.node_ff = nn.Sequential(nn.LayerNorm(width), nn.Linear(width, 4 * width), nn.SiLU(), nn.Linear(4 * width, width))

    def forward(self, work, nodes, memory_kv):
        work = work + self.read(self.norms[0](work), memory_kv)
        work = work + self.feedback(self.norms[1](work), self.feedback.project_memory(self.norms[2](nodes)))
        normalized = self.norms[3](work)
        work = work + self.interact(normalized, self.interact.project_memory(normalized))
        work = work + self.work_ff(work)
        nodes = nodes + self.write(self.norms[4](nodes), self.write.project_memory(self.norms[5](work)))
        return work, nodes + self.node_ff(nodes)


@dataclass
class PreparedReference:
    owner: int
    parameter_versions: tuple
    reference_versions: tuple
    conditioning: tuple
    sequence: tuple
    memory: torch.Tensor
    pair_memory: torch.Tensor
    kv: tuple
    empty_nodes: torch.Tensor
    empty_work: torch.Tensor


class ReferenceEditModel(nn.Module):
    def __init__(self, input_channels, single_channels, pair_channels=128, width=256,
                 workspace=32, blocks=4, heads=8, pair_width=128, pair_chunk=16):
        super().__init__()
        self.config = dict(input_channels=input_channels, single_channels=single_channels,
                           pair_channels=pair_channels, width=width, workspace=workspace,
                           blocks=blocks, heads=heads, pair_width=pair_width, pair_chunk=pair_chunk)
        self.inputs = nn.Sequential(nn.LayerNorm(input_channels), nn.Linear(input_channels, width))
        self.single = nn.Sequential(nn.LayerNorm(single_channels), nn.Linear(single_channels, width))
        self.pair_summary = nn.Sequential(nn.LayerNorm(2 * pair_channels), nn.Linear(2 * pair_channels, width))
        self.memory_norm = nn.LayerNorm(width)
        self.aa = nn.Embedding(20, width)
        self.edit = nn.Sequential(nn.Linear(3 * width, width), nn.SiLU(), nn.Linear(width, width))
        self.workspace = nn.Parameter(torch.randn(workspace, width) * .02)
        self.blocks = nn.ModuleList([EditWorkspaceBlock(width, heads) for _ in range(blocks)])
        self.input_out = nn.Linear(width, input_channels)
        self.single_out = nn.Linear(width, single_channels)
        self.pair_base = nn.Sequential(nn.LayerNorm(pair_channels), nn.Linear(pair_channels, pair_width))
        self.pair_left = nn.Linear(width, pair_width)
        self.pair_right = nn.Linear(width, pair_width)
        self.pair_work = nn.Linear(width, pair_width)
        self.pair_out = nn.Sequential(nn.SiLU(), nn.Linear(pair_width, pair_width), nn.SiLU(), nn.Linear(pair_width, pair_channels))
        # Small nonzero heads allow gradients into the full branch on the first step.
        for head in (self.input_out, self.single_out, self.pair_out[-1]):
            nn.init.normal_(head.weight, std=1e-3)
            nn.init.zeros_(head.bias)

    def versions(self):
        return tuple(p._version for p in self.parameters())

    def normalize_edits(self, sequence, edits):
        result = []
        for candidate in edits:
            seen = set()
            cleaned = []
            for position, original, target in candidate:
                if position in seen or not 0 <= position < len(sequence):
                    raise ValueError('duplicate or invalid edit position')
                seen.add(position)
                if sequence[position] != original or not 0 <= target < 20:
                    raise ValueError('edit does not match reference sequence')
                if original != target:
                    cleaned.append((position, original, target))
            result.append(tuple(sorted(cleaned)))
        if not result:
            raise ValueError('empty candidate batch')
        return result

    def propagate(self, memory, kv, sequence, edits):
        delta = memory.new_zeros(len(edits), len(sequence), memory.shape[-1])
        for b, candidate in enumerate(edits):
            for position, original, target in candidate:
                ids = torch.tensor([original, target], device=memory.device)
                old, new = self.aa(ids).unbind(0)
                delta[b, position] = self.edit(torch.cat((memory[position], old, new)))
        nodes = memory[None] + delta
        denominator = memory.new_tensor([max(len(e), 1) for e in edits])[:, None]
        summary = delta.sum(1) / denominator
        work = self.workspace[None].expand(len(edits), -1, -1) + summary[:, None]
        for block, keys in zip(self.blocks, kv):
            work, nodes = block(work, nodes, keys)
        return nodes, work

    def prepare_reference(self, conditioning, sequence):
        si, s, z = conditioning
        if si.ndim != 2 or s.ndim != 2 or z.shape[:2] != (len(s), len(s)) or len(sequence) != len(s):
            raise ValueError('reference shape mismatch')
        if len(si) != len(s) or any(not 0 <= int(a) < 20 for a in sequence):
            raise ValueError('invalid reference')
        sequence = tuple(map(int, sequence))
        memory = self.memory_norm(self.inputs(si) + self.single(s) + self.pair_summary(torch.cat((z.mean(0), z.mean(1)), -1)))
        kv = tuple(block.read.project_memory(memory) for block in self.blocks)
        empty_nodes, empty_work = self.propagate(memory, kv, sequence, [()])
        return PreparedReference(id(self), self.versions(), tuple(x._version for x in conditioning),
                                 conditioning, sequence, memory, self.pair_base(z), kv, empty_nodes, empty_work)

    def pair_write(self, base, nodes, work):
        left, right = self.pair_left(nodes), self.pair_right(nodes)
        summary = self.pair_work(work.mean(1))[:, None, None]
        chunks = []
        for start in range(0, nodes.shape[1], self.config['pair_chunk']):
            stop = start + self.config['pair_chunk']
            chunks.append(self.pair_out(base[None, start:stop] + left[:, start:stop, None] + right[:, None] + summary))
        return torch.cat(chunks, 1)

    def forward(self, reference, edits):
        if reference.owner != id(self) or reference.parameter_versions != self.versions():
            raise RuntimeError('reference projection cache belongs to another parameter version')
        if reference.reference_versions != tuple(x._version for x in reference.conditioning):
            raise RuntimeError('reference memory was modified')
        edits = self.normalize_edits(reference.sequence, edits)
        # Identical per-candidate kernel shapes avoid batch-position rounding
        # amplification when adding tiny updates to large native single values.
        # This pilot shares reference compute but does not claim parallel speedup.
        outputs = []
        for candidate in edits:
            nodes, work = self.propagate(reference.memory, reference.kv, reference.sequence, [candidate])
            si, s, z = reference.conditioning
            nonempty = float(bool(candidate))
            ds = (nodes - reference.empty_nodes) * nonempty
            dz = (self.pair_write(reference.pair_memory, nodes, work) -
                  self.pair_write(reference.pair_memory, reference.empty_nodes, reference.empty_work)) * nonempty
            outputs.append((si[None] + torch.nn.functional.linear(ds, self.input_out.weight),
                            s[None] + torch.nn.functional.linear(ds, self.single_out.weight),
                            z[None] + dz))
        return tuple(torch.cat([out[i] for out in outputs], 0) for i in range(3))
