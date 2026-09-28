"""Offline named collision audit against an explicitly stored covalent graph."""
from collections import deque
import numpy as np


def graph_neighbors(n, bonds):
    neighbors=[set() for _ in range(n)]
    for i,j in bonds:
        if i==j or not (0<=i<n and 0<=j<n):raise ValueError('invalid bond index')
        neighbors[int(i)].add(int(j));neighbors[int(j)].add(int(i))
    return neighbors


def graph_distance(neighbors, start, end):
    seen={start};queue=deque([(start,0)])
    while queue:
        node,d=queue.popleft()
        if node==end:return d
        for nxt in neighbors[node]-seen:
            seen.add(nxt);queue.append((nxt,d+1))
    return None


def verify_exclusions(n, bonds, pairs):
    neighbors=graph_neighbors(n,bonds)
    expected=np.triu(np.ones((n,n),dtype=bool),1)
    for i in range(n):
        seen={i};front={i}
        for _ in range(3):front={k for j in front for k in neighbors[j]}-seen;seen|=front
        for j in seen:
            if i<j:expected[i,j]=False
    actual=np.zeros_like(expected);actual[pairs[:,0],pairs[:,1]]=True
    return dict(exact=bool(np.array_equal(actual,expected)),duplicates=int(len(pairs)-actual.sum()),
                unexpected_included=int((actual&~expected).sum()),unexpected_excluded=int((expected&~actual).sum()))


def collision_records(coordinates, topology, names, residues, chains, sequence):
    x=np.asarray(coordinates,dtype=np.float64).reshape(-1,3);pairs=topology.pairs.numpy();radii=topology.radii.numpy().astype(np.float64)
    distances=np.linalg.norm(x[pairs[:,0]]-x[pairs[:,1]],axis=-1);depths=radii[pairs[:,0]]+radii[pairs[:,1]]-distances
    neighbors=graph_neighbors(len(x),topology.bonds.numpy())
    maximum=int(np.argmax(depths));selected=np.unique(np.r_[maximum,np.flatnonzero(distances<1.)])
    def atom(i):
        residue=int(residues[i]);return dict(index=int(i),chain=str(chains[i]),residue=residue,amino_acid=sequence[residue-1],name=str(names[i]))
    ca38=np.flatnonzero((np.asarray(residues)==38)&(np.asarray(names)=='CA'))
    if len(ca38)!=1:raise ValueError('expected one residue38 CA')
    rows=[]
    for k in selected:
        i,j=map(int,pairs[k]);a,b=atom(i),atom(j)
        rows.append(dict(a=a,b=b,distance=float(distances[k]),penetration=float(max(0,depths[k])),
                         severe=bool(distances[k]<1.),is_maximum=bool(k==maximum),
                         graph_distance=graph_distance(neighbors,i,j),
                         distance_to_res38_ca_min=float(min(np.linalg.norm(x[i]-x[ca38[0]]),np.linalg.norm(x[j]-x[ca38[0]]))),
                         near_y38_sequence=abs(a['residue']-38)<=2 or abs(b['residue']-38)<=2))
    return sorted(rows,key=lambda r:-r['penetration'])
