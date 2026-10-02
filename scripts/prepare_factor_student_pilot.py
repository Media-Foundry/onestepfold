"""Sequence-only selection for a new, bounded hard-response student pilot."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from fastglycan.sequence_isolation import read_hsps
from fastglycan.paired_teacher_protocol import sha256,write_json


def prepare_factor_student_pilot(root,pool_path,rank_lock,blast_bin):
    assert not (root/'selection.json').exists();root.mkdir(parents=True,exist_ok=True)
    pool=json.load(open(pool_path));old=json.load(open(rank_lock))['rows'];aa=set('ACDEFGHIKLMNPQRSTVWY')
    excluded={'1en7','5i27','2d00','3pmd','1l12','1l04','1tay','1tdy','1gob','2rn2','1izr','1izq'}
    rows={r['group_id']:r for r in pool['rows'] if r['role']=='train' and 80<=len(r['sequence'])<=192 and set(r['sequence'])<=aa and r.get('accessions') and r['pdb_id'].lower() not in excluded}
    records=dict(rows)
    for r in old:records[r['group_id']]=r
    aliases={g[:32]:g for g in records};assert len(aliases)==len(records)
    fasta=root/'all.fasta';fasta.write_text(''.join(f'>{g[:32]}\n{r["sequence"]}\n' for g,r in sorted(records.items())))
    commands=[[str(blast_bin/'makeblastdb'),'-in',str(fasta),'-dbtype','prot','-parse_seqids','-out',str(root/'db')],
      [str(blast_bin/'blastp'),'-task','blastp','-query',str(fasta),'-db',str(root/'db'),'-out',str(root/'hits.tsv'),'-outfmt','6 qseqid sseqid qlen slen evalue qseq sseq','-word_size','3','-matrix','BLOSUM62','-gapopen','11','-gapextend','1','-seg','yes','-comp_based_stats','2','-evalue','0.001','-max_target_seqs',str(len(records)),'-num_threads','8']]
    write_json(root/'selection_protocol.json',dict(pool_sha256=sha256(pool_path),old_panel_sha256=sha256(rank_lock),source_sha256=sha256(Path(__file__)),commands=commands,split_counts=dict(train=16,validation=8),sites_per_parent=2,rule='reuse calibrated HSP near/domain policy; union with shared accessions; one selected parent per component; exclude old rank-panel components',tools={n:dict(sha256=sha256(blast_bin/n),version=subprocess.check_output([str(blast_bin/n),'-version'],text=True)) for n in ['blastp','makeblastdb']}))
    for i,cmd in enumerate(commands):
        with open(root/f'select_{i}.log','w') as log:subprocess.run(cmd,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=180)
    parent={g:g for g in records}
    def find(g):
        while parent[g]!=g:parent[g]=parent[parent[g]];g=parent[g]
        return g
    def union(a,b):
        a,b=find(a),find(b)
        if a!=b:parent[max(a,b)]=min(a,b)
    evidence=[]
    for h in read_hsps(root/'hits.tsv'):
        a,b=aliases[h.query],aliases[h.subject];e=h.evidence()
        if a!=b and e['excluded']:union(a,b);evidence.append(dict(query=a,subject=b,**e))
    acc={}
    for g,r in records.items():
        for a in r.get('accessions',[]):
            if a in acc:union(g,acc[a])
            else:acc[a]=g
    blocked={find(r['group_id']) for r in old};used=set(blocked);selected=[];candidates=[]
    def key(g,tag='parent'):return hashlib.sha256(('factor-student-v1:20261002:'+tag+':'+g).encode()).hexdigest()
    for lo,hi,nval in [(80,112,3),(113,150,3),(151,192,2)]:
        group=[]
        for g in sorted(rows,key=key):
            r=rows[g];component=find(g)
            if not lo<=len(r['sequence'])<=hi or component in used:continue
            used.add(component);group.append(r)
            if len(group)==8:break
        assert len(group)==8,(lo,hi,len(group))
        for j,r in enumerate(group):
            positions=sorted(range(len(r['sequence'])),key=lambda pos:key(r['group_id']+':'+str(pos),'site'))[:2]
            selected.append(dict(index=len(selected),group_id=r['group_id'],pdb_id=r['pdb_id'],sequence=r['sequence'],accessions=r['accessions'],component=find(r['group_id']),positions=positions,role='validation' if j<nval else 'train',source_metadata=r,stratum=[lo,hi]))
    assert len(selected)==24 and len({r['component'] for r in selected})==24
    assignments=[[] for _ in range(8)];load=[0]*8
    for r in sorted(selected,key=lambda r:len(r['sequence']),reverse=True):
        i=min(range(8),key=lambda i:load[i]);assignments[i].append(r['index']);load[i]+=len(r['sequence'])**2
    write_json(root/'selection.json',dict(complete=True,rows=selected,assignments=assignments,pool_eligible=len(rows),components=len({find(g) for g in records}),all_components={g:find(g) for g in records},blocked_components=sorted(blocked),excluded_edges=evidence,weights_sha256=pool['weights_sha256'],aa='ACDEFGHIKLMNPQRSTVWY',teacher_unique=936,teacher_with_replays=960,expected_recycles=3840,training_count=16,validation_count=8,hits_sha256=sha256(root/'hits.tsv'),scope='new parents for mutation-response student, historical folding TRAIN pool; no claim of pretraining-unseen or remote-homology absence'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--pool',type=Path,required=True);p.add_argument('--rank-lock',type=Path,required=True);p.add_argument('--blast-bin',type=Path,required=True);a=p.parse_args();prepare_factor_student_pilot(a.root,a.pool,a.rank_lock,a.blast_bin)
