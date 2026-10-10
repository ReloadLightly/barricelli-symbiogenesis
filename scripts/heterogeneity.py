#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Matched constituent-rule and layout controls, confirmation and damage replay."""
import itertools,json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from barricelli.run import ROOT,run,read_csv,save_json
from barricelli.descriptors import describe,bootstrap_mean_ci
import numpy as np
RULES=['galloway_A','galloway_B','galloway_AB_halves','galloway_AB_quarters','galloway_AB_temporal']

def main():
 base=ROOT/'results/heterogeneity'; base.mkdir(parents=True,exist_ok=True)
 plans=[]
 for cohort,seeds,steps in [('exploration',range(6100,6108),512),('confirmation',range(9200,9204),2048)]:
  for seed,rule in itertools.product(seeds,RULES):
   conf={'model':'research','variant':rule+'_scaled','norm':rule,'width':128,'steps':steps,'boundary':'ring','iteration_order':'ascending','initialization':'designed_random','seed':seed,
    'alphabet':[-9,-7,-3,1,5,9,11],'density':.35,'layout':'uniform',
    'modifications':['scaled width128; published-style sequential original-source-relative copying with three-attempt cap','explicit collision rule: '+rule,'whole-ring old-row nearest-number lookup across norm boundaries']}
   plans.append({'id':f'{cohort}_{seed}_{rule}','cohort':cohort,'config':conf})
 design={'declared_before_execution':True,'runs':plans,'primary_contrast':'spatial AB minus mean of homogeneous A andB on paired seeds; temporal AB separates spatial layout from constituent mixing',
  'spatial_layouts':{'AB_halves':'A at x0..63; B at64..127','AB_quarters':'A/B/A/B in32-cell intervals'},'temporal_control':'whole world A on even update times andB on odd times',
  'units':'initial-state seeds; timepoints are not replicates','confirmation':'four unseen seeds9200..9203 at four-times horizon; chosen before exploration outcomes',
  'damage':'exploration cohorts: saved row256, clear x48..55, replay128 updates; compare stored undamaged rows256..384; external intervention explicitly logged',
  'limits':['repeated k-mers are structural diagnostics, not viable collectives','recurrence is right-censored when absent','no exchange treatment or unlimited-evolution claim']}
 save_json(base/'manifest.json',design); rows=[]
 for plan in plans:
  out=base/plan['id']; out.mkdir(exist_ok=True)
  if (out/'descriptors.json').exists(): stats=json.loads((out/'statistics.json').read_text()); desc=json.loads((out/'descriptors.json').read_text())
  else:
   stats=run(plan['config'],out); desc=describe(read_csv(out/'trajectory.csv'),stats,boundary=plan['config']['boundary']); save_json(out/'descriptors.json',desc)
  rows.append({'id':plan['id'],'cohort':plan['cohort'],'seed':plan['config']['seed'],'norm':plan['config']['norm'],'path':str(out.relative_to(ROOT)),**desc,'engine_seconds':stats['engine_seconds'],'process_seconds':stats['process_seconds'],'max_rss_kib':stats['max_rss_kib']})
 # Verify paired rows before attributing treatment differences.
 for cohort,seeds,_ in [('exploration',range(6100,6108),512),('confirmation',range(9200,9204),2048)]:
  for seed in seeds:
   initials=[read_csv(base/f'{cohort}_{seed}_{rule}'/'initial.csv')[0] for rule in RULES]
   if not all(np.array_equal(initials[0],r) for r in initials[1:]): raise RuntimeError('unpaired initial rows')
 perturbations=[]; perturbplans=[]
 for plan in plans:
  if plan['cohort']!='exploration': continue
  arr=read_csv(base/plan['id']/'trajectory.csv'); initial=arr[256].copy(); initial[48:56]=0
  out=base/(plan['id']+'__damage'); out.mkdir(exist_ok=True); np.savetxt(out/'frozen.csv',initial[None,:],fmt='%d',delimiter=',')
  conf=dict(plan['config']); conf.update(initial_state_file=str((out/'frozen.csv').relative_to(ROOT)),seed=None,steps=128)
  conf['modifications']=conf['modifications']+['EXTERNAL INTERVENTION: clear x48..55 in baseline row256, restart time at0']
  perturbplans.append({'id':out.name,'config':conf,'paired_undamaged':plan['id'],'baseline_time':256,'removed_cells':int(np.count_nonzero(arr[256,48:56]))})
 save_json(base/'damage_manifest.json',{'declared_before_damage_execution':True,'runs':perturbplans})
 for plan in perturbplans:
  out=base/plan['id']
  if (out/'damage_outcome.json').exists(): measured=json.loads((out/'damage_outcome.json').read_text())
  else:
   stats=run(plan['config'],out); desc=describe(read_csv(out/'trajectory.csv'),stats,boundary=plan['config']['boundary'])
   undamaged=read_csv(base/plan['paired_undamaged']/'trajectory.csv')[256:385]; control=describe(undamaged,boundary=plan['config']['boundary'])
   measured={'id':plan['id'],'seed':int(plan['paired_undamaged'].split('_')[1]),'norm':plan['config']['norm'],'removed_cells':plan['removed_cells'],'damaged':desc,'undamaged_saved_window':control,
    'occupancy_difference':desc['tail_occupancy']-control['tail_occupancy'],'repeated4_difference':desc['tail_repeated4_fraction']-control['tail_repeated4_fraction'],'process_seconds':stats['process_seconds']}
   save_json(out/'damage_outcome.json',measured)
  perturbations.append(measured)
 contrasts=[]
 for cohort in ['exploration','confirmation']:
  seeds=sorted(set(r['seed'] for r in rows if r['cohort']==cohort))
  for treatment in RULES[2:]:
   metrics={}
   for metric in ['tail_activity','tail_repeated4_fraction','retained_repeated4_signatures','tail_new4_signatures']:
    diffs=[]
    for seed in seeds:
     group={r['norm']:r for r in rows if r['cohort']==cohort and r['seed']==seed}
     diffs.append(group[treatment][metric]-.5*(group['galloway_A'][metric]+group['galloway_B'][metric]))
    metrics[metric]=bootstrap_mean_ci(diffs)
   contrasts.append({'cohort':cohort,'treatment':treatment,'contrast':'minus paired mean(A,B)','metrics':metrics})
 save_json(base/'summary.json',{'rows':rows,'contrasts':contrasts,'damage':perturbations,'interpretation':'organization descriptors and recurrence, not reproduction or inherited collective diversity'})
 print(json.dumps(contrasts,indent=2))
if __name__=='__main__': main()
