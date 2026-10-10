#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Resumable equal-budget random/archive/conversational-Codex comparison."""
import argparse,itertools,json,pathlib,sys,time,datetime,collections
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from barricelli.run import ROOT,run,read_csv,save_json,sha
from barricelli.descriptors import describe,coverage,mean_nearest_diversity,bootstrap_mean_ci
import numpy as np
BASE=ROOT/'results/search'; METHODS=['random','novelty_archive','codex_feedback']; REPEATS=4; BUDGET=12
ALPHABETS=[[-1,1],[-3,1,5],[-5,-3,1,3,5],[-9,-7,-3,1,5,9,11]]
SPACE=[{'alphabet_id':a,'density':d,'layout':layout} for a,d,layout in itertools.product(range(4),[.15,.35,.65,.9],['uniform','center_patch','two_patches'])]

def records(method,repeat):
 paths=sorted((BASE/method/f'repeat{repeat}').glob('trial*/search_record.json'))
 return [json.loads(p.read_text()) for p in paths]
def execute(method,repeat,trial,index,reason):
 out=BASE/method/f'repeat{repeat}'/f'trial{trial:02d}'; out.mkdir(parents=True,exist_ok=True)
 if (out/'search_record.json').exists(): return json.loads((out/'search_record.json').read_text())
 theta=SPACE[index]; conf={'model':'research','variant':'galloway_B_scaled','norm':'galloway_B','width':128,'steps':256,'boundary':'ring','iteration_order':'ascending','seed':4100+100*repeat+trial,'initialization':'designed_random',
  'alphabet':ALPHABETS[theta['alphabet_id']],'density':theta['density'],'layout':theta['layout'],
  'modifications':['ring width128 and256 updates; independently authored published-style B update; designed random initial distribution'],
  'search':{'method':method,'repeat':repeat,'trial':trial,'space_index':index}}
 save_json(out/'planned.json',{'config':conf,'reason':reason,'declared_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 stats=run(conf,out); descriptors=describe(read_csv(out/'trajectory.csv'),stats)
 previous=records(method,repeat); vector=np.array(descriptors['vector'])
 novelty=float(np.mean(sorted(np.linalg.norm(vector-np.array(r['descriptors']['vector'])) for r in previous)[:3])) if previous else None
 record={'method':method,'repeat':repeat,'trial':trial,'space_index':index,'theta':theta,'seed':conf['seed'],'path':str(out.relative_to(ROOT)),
  'reason':reason,'descriptors':descriptors,'novelty_to_previous_knn3':novelty,'engine_seconds':stats['engine_seconds'],'process_seconds':stats['process_seconds'],'max_rss_kib':stats['max_rss_kib']}
 save_json(out/'search_record.json',record); return record

def bootstrap():
 BASE.mkdir(parents=True,exist_ok=True)
 if not (BASE/'design.json').exists():
  save_json(BASE/'design.json',{'declared_before_execution':True,'methods':METHODS,'repeated_searches':REPEATS,'evaluations_per_search':BUDGET,'width':128,'steps':256,'update_budget_per_search':128*256*BUDGET,'space':SPACE,'alphabets':ALPHABETS,
   'shared_bootstrap':'first4 configurations and seed schedule identical across methods; actual simulation executions counted for each method',
   'random_policy':'uniform configuration index, without replacement after shared bootstrap',
   'novelty_policy':'select evaluated parent with largest mean three-nearest descriptor distance; sample an untested one-factor neighbor; fall back to untested random',
   'codex_policy':'two conversational feedback rounds, four proposals per repeated search per round; admissible configuration indexes only; logs retained',
   'fixed_renderer':'configs/palette.json; numerical descriptors do not depend on renderer','primary_measure':'coverage in5×5×5 occupancy/activity/repeated4 archive; nearest-neighbor diversity supplementary',
   'model_use':{'automated_integration':False,'external_api_calls':0,'paid_calls':0,'token_cost':'not separately metered by the conversational interface'},'confirmation_seeds':[9100,9101,9102,9103]})
 for repeat in range(REPEATS):
  rng=np.random.default_rng(700+repeat); initial=list(map(int,rng.choice(len(SPACE),4,replace=False)))
  for method in METHODS:
   for trial,index in enumerate(initial): execute(method,repeat,trial,index,'shared initial exploration')
  for method in METHODS[:2]:
   for trial in range(4,BUDGET):
    history=records(method,repeat); tested={r['space_index'] for r in history}; available=[i for i in range(len(SPACE)) if i not in tested]
    rng=np.random.default_rng(8000+100*repeat+trial+(1000 if method=='novelty_archive' else 0))
    if method=='novelty_archive':
     vectors=np.array([r['descriptors']['vector'] for r in history]); d=np.sqrt(np.sum((vectors[:,None]-vectors[None,:])**2,axis=-1)); np.fill_diagonal(d,np.inf)
     scores=np.sort(d,axis=1)[:,:min(3,len(history)-1)].mean(axis=1); parent=history[int(np.argmax(scores))]['theta']
     neighbors=[i for i in available if sum(SPACE[i][k]!=parent[k] for k in parent)==1]
     index=int(rng.choice(neighbors or available)); reason='descriptor-novel parent; untested one-factor neighbor'
    else: index=int(rng.choice(available)); reason='uniform untested configuration'
    execute(method,repeat,trial,index,reason)
 feedback(0)

def feedback(batch):
 if (BASE/f'feedback{batch}.json').exists(): return
 report={'batch':batch,'generated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'instructions':'Propose four untested admissible space indexes per repeat to expand descriptor archive coverage. No renderer/rule changes. Every proposal is a hypothesis; use feedback and retain all outcomes.',
  'space':SPACE,'repeats':{str(r):records('codex_feedback',r) for r in range(REPEATS)}}
 save_json(BASE/f'feedback{batch}.json',report)
 for r in range(REPEATS):
  print('repeat',r,'coverage',coverage(records('codex_feedback',r)))
  for rec in records('codex_feedback',r): print(rec['space_index'],rec['theta'],[round(v,3) for v in rec['descriptors']['vector']],rec['descriptors']['retained_repeated4_signatures'])

def proposals(path):
 proposal=json.loads(pathlib.Path(path).read_text()); batch=proposal['batch']; source=BASE/f'feedback{batch-1}.json'
 if proposal['feedback_sha256']!=sha(source): raise ValueError('proposal feedback hash mismatch')
 save_json(BASE/f'codex_proposals{batch}.json',proposal)
 for repeat in range(REPEATS):
  entries=proposal['repeats'][str(repeat)]; tested={r['space_index'] for r in records('codex_feedback',repeat)}
  if len(entries)!=4: raise ValueError('exactly four proposals per repeat/batch')
  for offset,entry in enumerate(entries):
   index=entry['space_index']; trial=4*batch+offset
   if not 0<=index<len(SPACE): raise ValueError('outside admissible space')
   if not (BASE/'codex_feedback'/f'repeat{repeat}'/f'trial{trial:02d}'/'search_record.json').exists() and index in tested: raise ValueError('proposal repeats tested configuration')
   execute('codex_feedback',repeat,trial,index,entry['hypothesis']); tested.add(index)
 feedback(batch)
 if batch==2: summary()

def summary():
 results=[]
 for method in METHODS:
  for repeat in range(REPEATS):
   history=records(method,repeat)
   if len(history)!=BUDGET: raise ValueError('unequal completed budgets')
   results.append({'method':method,'repeat':repeat,'evaluations':len(history),'cell_updates':len(history)*128*256,'archive_coverage':coverage(history),'nearest_diversity':mean_nearest_diversity(history),
    'engine_seconds':sum(r['engine_seconds'] for r in history),'process_seconds':sum(r['process_seconds'] for r in history),'descriptor_seconds':sum(r['descriptors']['descriptor_seconds'] for r in history),
    'highest_repeat4':max(r['descriptors']['tail_repeated4_fraction'] for r in history)})
 aggregate={m:{'coverage':bootstrap_mean_ci([r['archive_coverage'] for r in results if r['method']==m]),'diversity':bootstrap_mean_ci([r['nearest_diversity'] for r in results if r['method']==m])} for m in METHODS}
 paired={m:bootstrap_mean_ci([next(r['archive_coverage'] for r in results if r['method']==m and r['repeat']==i)-next(r['archive_coverage'] for r in results if r['method']=='random' and r['repeat']==i) for i in range(REPEATS)]) for m in METHODS[1:]}
 save_json(BASE/'summary.json',{'searches':results,'aggregate':aggregate,'paired_coverage_difference_vs_random':paired,'interpretation':'exploratory low-budget comparison; four search units; Codex shares conversation context; no broad model-performance or biological claim'})
 print(json.dumps(aggregate,indent=2))

def replay():
 design=json.loads((BASE/'design.json').read_text())
 if design['space']!=SPACE: raise ValueError('search space changed')
 # Replay exact recorded adaptive proposals; no model calls during regeneration.
 bootstrap()
 for batch in [1,2]: proposals(BASE/f'codex_proposals{batch}.json')

if __name__=='__main__':
 p=argparse.ArgumentParser(); p.add_argument('--phase',choices=['bootstrap','proposals','summary','replay'],required=True); p.add_argument('--file'); a=p.parse_args()
 if a.phase=='bootstrap': bootstrap()
 elif a.phase=='proposals': proposals(a.file)
 elif a.phase=='replay': replay()
 else: summary()
