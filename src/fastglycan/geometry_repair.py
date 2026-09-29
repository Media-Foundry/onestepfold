"""Restrained force-field baseline, separate from folding and its design objective."""
import io
import random
import numpy as np

AA3 = dict(zip('ARNDCQEGHILKMFPSTWYV',
               'ALA ARG ASN ASP CYS GLN GLU GLY HIS ILE LEU LYS MET PHE PRO SER THR TRP TYR VAL'.split()))


def identity_indices(expected, actual):
    """Map immutable atom identities; duplicates and missing atoms are errors."""
    if len(set(expected)) != len(expected) or len(set(actual)) != len(actual):
        raise ValueError('duplicate atom identity')
    lookup = {key: i for i, key in enumerate(actual)}
    if not set(expected) <= set(actual):
        raise ValueError('missing original atom')
    return np.array([lookup[key] for key in expected], dtype=int)


def preservation(raw, repaired, ca):
    raw, repaired = np.asarray(raw).reshape(-1, 3), np.asarray(repaired).reshape(-1, 3)
    if raw.shape != repaired.shape or not np.isfinite(repaired).all():
        raise ValueError('invalid repaired coordinates')
    ca = np.asarray(ca).reshape(-1)
    delta = repaired - raw
    a, b = repaired[ca], raw[ca]
    ac, bc = a-a.mean(0), b-b.mean(0)
    u, _, vt = np.linalg.svd(ac.T @ bc)
    rotation = u @ np.diag([1, 1, np.linalg.det(u @ vt)]) @ vt
    pd = np.linalg.norm(a[:, None]-a[None, :], axis=-1)-np.linalg.norm(b[:, None]-b[None, :], axis=-1)
    upper = np.triu_indices(len(ca), 1)
    result = dict(heavy_rms=float(np.sqrt(np.mean(np.sum(delta**2, axis=-1)))),
                  ca_rms=float(np.sqrt(np.mean(np.sum(delta[ca]**2, axis=-1)))),
                  ca_aligned_rms=float(np.sqrt(np.mean(np.sum((ac@rotation-bc)**2, axis=-1)))),
                  max_displacement=float(np.linalg.norm(delta, axis=-1).max()),
                  ca_distance_rms=float(np.sqrt(np.mean(pd[upper]**2))))
    result['accepted'] = result['heavy_rms'] <= 2 and result['ca_rms'] <= 1
    return result


def force_diagnostics(forces):
    """Residual forces in kJ/mol/nm; neither diagnostic is a termination code."""
    forces = np.asarray(forces, dtype=np.float64)
    if forces.ndim != 2 or forces.shape[1] != 3 or not len(forces) or not np.isfinite(forces).all():
        raise ValueError('invalid residual forces')
    vector = float(np.sqrt(np.mean(np.sum(forces**2, axis=-1))))
    component = float(np.sqrt(np.mean(forces**2)))
    return dict(force_rms_vector=vector, force_vector_rms_le_10=vector <= 10.,
                force_rms_component=component, force_component_rms_le_10=component <= 10.,
                force_units='kJ/mol/nm')


def repair_coordinates(raw, names, residues, chains, sequence, bonds):
    """Return original-heavy Å coordinates, full auxiliary structure and audit.

    Imports are lazy so identity/preservation tests do not require OpenMM.
    """
    import openmm as mm
    from openmm import app, unit
    from pdbfixer import PDBFixer
    random.seed(6271)
    np.random.seed(6271)
    raw = np.asarray(raw, dtype=np.float64).reshape(-1, 3)
    expected = [(str(c), int(r), str(n)) for c, r, n in zip(chains, residues, names)]
    topology = app.Topology()
    chain_map, residue_map, atoms = {}, {}, []
    for c, r, n in expected:
        if c not in chain_map:
            chain_map[c] = topology.addChain(c)
        if (c, r) not in residue_map:
            residue_map[c, r] = topology.addResidue(AA3[sequence[r-1]], chain_map[c], str(r))
        atoms.append(topology.addAtom(n, app.Element.getBySymbol(n[0]), residue_map[c, r]))
    for i, j in bonds:
        topology.addBond(atoms[int(i)], atoms[int(j)])
    positions = raw * .1 * unit.nanometer
    text = io.StringIO()
    app.PDBFile.writeFile(topology, positions, text, keepIds=True)
    fixer = PDBFixer(pdbfile=io.StringIO(text.getvalue()), platform=mm.Platform.getPlatformByName('CPU'))
    # PDB parsing can infer bonds; replace it with the archived graph and exact positions.
    fixer.topology, fixer.positions = topology, positions
    fixer.missingResidues = {}
    fixer.findMissingAtoms()
    if any(fixer.missingAtoms.values()):
        raise ValueError('missing internal heavy atoms')
    if any(set(v)-{'OXT'} for v in fixer.missingTerminals.values()):
        raise ValueError('unexpected terminal atoms')
    fixer.addMissingAtoms(seed=6271)
    def ids(top):
        return [(a.residue.chain.id, int(a.residue.id), a.name) for a in top.atoms()]
    def restore(top, pos):
        array = np.array(pos.value_in_unit(unit.nanometer))
        ix = identity_indices(expected, ids(top))
        array[ix] = raw * .1
        return array * unit.nanometer
    fixer.positions = restore(fixer.topology, fixer.positions)
    ff = app.ForceField('amber14/protein.ff14SB.xml', 'implicit/gbn2.xml')
    modeller = app.Modeller(fixer.topology, fixer.positions)
    variants = modeller.addHydrogens(ff, pH=7.0, platform=mm.Platform.getPlatformByName('CPU'))
    modeller.positions = restore(modeller.topology, modeller.positions)
    actual = ids(modeller.topology)
    ix = identity_indices(expected, actual)
    reverse = {int(j): i for i, j in enumerate(ix)}
    old_bonds = {tuple(sorted(map(int, b))) for b in bonds}
    mapped = {tuple(sorted((reverse[a.index], reverse[b.index]))) for a, b in modeller.topology.bonds()
              if a.index in reverse and b.index in reverse}
    if mapped != old_bonds:
        raise ValueError('original heavy graph changed')
    added = [a for a in modeller.topology.atoms() if a.index not in reverse]
    if any(a.element.symbol != 'H' and a.name != 'OXT' for a in added):
        raise ValueError('unexpected added heavy atom')
    system = ff.createSystem(modeller.topology, nonbondedMethod=app.NoCutoff,
                             constraints=None, removeCMMotion=False)
    force = mm.CustomExternalForce('0.5*k*((x-x0)^2+(y-y0)^2+(z-z0)^2)')
    force.addGlobalParameter('k', 1000.)
    for name in ['x0', 'y0', 'z0']:
        force.addPerParticleParameter(name)
    for j, xyz in zip(ix, raw*.1):
        force.addParticle(int(j), xyz.tolist())
    system.addForce(force)
    integrator = mm.VerletIntegrator(.001)
    context = mm.Context(system, integrator, mm.Platform.getPlatformByName('CPU'), {'Threads': '2'})
    context.setPositions(modeller.positions)
    before = context.getState(getEnergy=True).getPotentialEnergy().value_in_unit(unit.kilojoule_per_mole)
    if not np.isfinite(before):
        raise ValueError('nonfinite starting energy')
    mm.LocalEnergyMinimizer.minimize(context, 10., 2000)
    state = context.getState(getPositions=True, getEnergy=True, getForces=True)
    full = np.asarray(state.getPositions(asNumpy=True).value_in_unit(unit.angstrom))
    energy = state.getPotentialEnergy().value_in_unit(unit.kilojoule_per_mole)
    forces = np.asarray(state.getForces(asNumpy=True).value_in_unit(unit.kilojoule_per_mole/unit.nanometer))
    diagnostics = force_diagnostics(forces)
    if not np.isfinite(full).all() or not np.isfinite(energy):
        raise ValueError('nonfinite minimization output')
    pdb = io.StringIO()
    app.PDBFile.writeFile(modeller.topology, state.getPositions(), pdb, keepIds=True)
    return full[ix], full, pdb.getvalue(), dict(energy_before=before, energy_after=energy,
        **diagnostics,
        convergence_note='post-hoc residual force diagnostics only; termination reason and iteration count not recorded; maximum 2000 iterations, no retry',
        original_graph_exact=True, original_positions_restored=True,
        added_atoms=[dict(identity=actual[a.index], element=a.element.symbol) for a in added],
        protonation_variants=variants, original_indices=ix.tolist())
