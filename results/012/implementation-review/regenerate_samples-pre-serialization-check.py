"""Regenerate six prespecified detector partitions; preserve every discrepancy."""
import argparse,gzip,hashlib,json,os,sys,time
from pathlib import Path
for name in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[name]='1'
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--packet',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
sys.path.insert(0,str(a.packet/'repo'))
from eegt import event_study as study,waveform_events as wave
start=time.process_time();differences=[];counts=[]
native=np.load(a.packet/'repo/data/derived/012/native-selected.npz');prepared=np.load(a.packet/'repo/data/derived/010/prepared.npz')
selected=[r for r in json.loads((a.packet/'repo/results/010/prepared.json').read_text())['records'] if r['status']=='ELIGIBLE']
def compare(x,y,path):
 if type(x)!=type(y):differences.append({'path':path,'kind':'TYPE','recorded_type':type(x).__name__,'regenerated_type':type(y).__name__});return
 if isinstance(x,dict):
  if set(x)!=set(y):differences.append({'path':path,'kind':'KEYS'});return
  for k in x:compare(x[k],y[k],path+'/'+k)
 elif isinstance(x,list):
  if len(x)!=len(y):differences.append({'path':path,'kind':'LENGTH','recorded':len(x),'regenerated':len(y)});return
  for i,(u,v) in enumerate(zip(x,y)):compare(u,v,path+'/'+str(i))
 elif x!=y:differences.append({'path':path,'kind':'SCALAR','recorded':x,'regenerated':y})
for i in [0,61,121]:
 for branch,name in [('native','primary'),('prepared','original')]:
  path=a.packet/'repo/data/derived/012/events'/f'row-{i:03d}'/f'{branch}-{name}.jsonl.gz'
  with gzip.open(path,'rt') as f:
   header=json.loads(next(f))['value'];events=[json.loads(line)['value'] for line in f]
  original=dict(header['result'],events=events)
  if branch=='native':x,mask,config,transform=study.native_variant(native['samples_uv'][i],native['valid'][i],name,selected[i]['candidate_index'])
  else:x=prepared['patches'][i].reshape(4,6000).astype(np.float64)*100;mask=np.ones(x.shape,dtype=bool);config={}
  regenerated=wave.discover(x,250 if branch=='native' else 200,mask,[(0,x.shape[1],0.)],include_cycles=branch=='native',include_envelopes=branch=='native',**config)
  before=len(differences);compare(original,regenerated,f'row-{i:03d}/{branch}-{name}')
  counts.append({'array_row':i,'branch':branch,'variant':name,'recorded_events':len(events),'regenerated_events':len(regenerated['events']),'differences':len(differences)-before,'partition_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
r={'schema':'eegt-detector-sample-regeneration/v1','status':'EXACT_MATCH' if not differences else 'DIFFERENCES_RETAINED','selection':[0,61,121],'selection_basis':'EMPIRICAL-AUDIT-PLAN.json fixed before full result inspection','partitions':counts,'difference_count':len(differences),'differences':differences,'cpu_seconds':time.process_time()-start,'scope':'Six partitions: full native primary morphology and prepared original landmarks; not all2,806partitions.'}
a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='differences'}))
