from pathlib import Path
import importlib.util,json,itertools,statistics,hashlib
import numpy as np
from scipy.stats import spearmanr
from scipy.spatial.distance import pdist
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('eegt.root_event_review',HERE/'event_study.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
checks=0
def check(x,msg):
 global checks
 assert x,msg
 checks+=1
pairs=list(itertools.combinations(range(8),2))
for seed in range(5):
 base=np.random.default_rng(seed).integers(1,50,size=16)
 v=np.arange(1,9)[:,None]*base
 _,reason=m._cosine_pairs(v,pairs)
 check(reason=='CONSTANT_DISTANCE_VECTOR','analytic proportional geometry must abstain')
# Four channels; bins derive from integer sample indices, not interpolation.
r={'sample_rate_hz':200,'runs':[{'channel_key':f'channel_{i}','status':'OK','start_sample':0,'end_sample':6000,'guard_samples':400,'segment_start_sample':0,'clock_start_seconds':0} for i in range(4)],'events':[]}
for ch in range(4):
 for idx in [399,400,599,600,5599,5600]:
  for fam,label in m.COMPONENTS:
   r['events'].append({'accepted':True,'family':fam,'polarity':label if fam=='extremum' else None,'direction':label if fam=='inflection' else None,'index':idx,'fractional_index':idx+.7,'channel_key':f'channel_{ch}'})
c,e=m.event_counts(r)
check(e==list(range(2,28)),'whole-second support differs')
for ch in range(4):
 for component in range(4):
  check(c[1,4*ch+component]==1 and c[2,4*ch+component]==2 and c[3,4*ch+component]==1,'integer bins differ')
  check(c[27,4*ch+component]==1 and c[28,4*ch+component]==1,'end bins differ')
# Empty native rows still yield four strata, four channels, three tolerances.
native={**r,'sample_rate_hz':250,'events':[]}
t,matches=m.native_matches(native,native,'gain_x2')
check(len(t)==4 and len(matches)==48,'empty strata missing')
check(all(x['agreement'] is None and x['n_a']==x['n_b']==0 for x in matches),'empty agreement fabricated')
# Independent scipy distance/rank route on nondegenerate artificial vectors.
rng=np.random.default_rng(771);counts=rng.integers(1,40,size=(30,16));latent=rng.normal(size=(30,200));k=[1,2,3,4,8,9,10,11,12];adj=[(a,b) for a,b in zip(k,k[1:]) if b==a+1]
value=m.metric_result(counts,latent,k,adj,'geometry')
expected=float(spearmanr(pdist(counts[k].astype(float),'cosine'),pdist(latent[k],'cosine')).statistic)
check(abs(value['rho']-expected)<1e-12,'independent geometry mismatch')
check(all(b==a+1 for a,b in m.support_indices(k,k)[1]),'bridged missing interval')
zero=counts.copy();zero[12]=0
check(m.metric_result(zero,latent,k,adj,'geometry')['rho'] is None,'zero required geometry vector salvaged')
for n in range(2,7):
 v=np.arange(1,n+1)/100
 actual=m.exact_signflip(v)
 scores=[statistics.mean(float(v[i])*sgn[i] for i in range(n)) for sgn in itertools.product([-1,1],repeat=n)]
 p=sum(abs(x)>=abs(statistics.mean(v))-1e-12 for x in scores)/len(scores)
 check(actual['p_two_sided']==p and actual['p_bonferroni_four']==min(1,4*p),'exact null mismatch')
# Separate participant hierarchy; source-local IDs enter this evaluator only.
root=HERE.parents[2]/'outputs/eegt'
selected=[x for x in json.loads((root/'results/010/prepared.json').read_text())['records'] if x['status']=='ELIGIBLE']
rows=[]
for x in selected:
 for model in m.MODELS:
  for metric in m.METRICS:
   val=int(x['source_subject'])/100+(-1)**x['candidate_index']*(x['candidate_index']%17)/1000
   rows.append({'candidate_index':x['candidate_index'],'model':model,'metric':metric,'effect':val,'reason':None})
agg=m.aggregate_effects(rows,selected)
for endpoint in agg:
 expected=[]
 for person in sorted(set(x['source_subject'] for x in selected)):
  nights=[]
  for night in ['001','002']:
   ids={x['candidate_index'] for x in selected if x['source_subject']==person and x['session']==night}
   values=[x['effect'] for x in rows if x['candidate_index'] in ids and x['model']==endpoint['model'] and x['metric']==endpoint['metric']]
   if len(values)>=3:nights.append(statistics.median(values))
  if len(nights)==2:expected.append(statistics.mean(nights))
 check(endpoint['test']['n']==5,'expected five complete synthetic participants')
 check(abs(endpoint['test']['observed_mean']-statistics.mean(expected))<1e-14,'hierarchical weighting mismatch')
report={'status':'PASS','assertions':checks,'source_sha256':hashlib.sha256((HERE/'event_study.py').read_bytes()).hexdigest(),'scope':'Independent analytic arithmetic, counts, empty strata, support and hierarchy; no empirical event detector calls','warnings':['paired_valid_blocks in helper summary includes all valid paired blocks, including incomplete people; public primary-block denominator must use COMPLETE people only']}
(HERE/'analytic-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
