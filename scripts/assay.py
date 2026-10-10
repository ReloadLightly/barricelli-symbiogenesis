#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Paired organization/partner assay, with conservative detached-copy criterion."""
import sys,pathlib,json,csv,itertools
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from barricelli.run import ROOT,run,read_csv,save_json
from barricelli.motifs import matches,outcome,disjoint
import numpy as np
WIDTH=256; STEPS=48; PLACEMENTS=[16,112,232]

def conditions(motif):
 motif=np.array(motif,dtype=np.int32); helper=int(np.flatnonzero(motif<0)[0]); values=sorted(set(motif)-{0})
 variants={'intact':motif.copy()}
 for value in values: variants[f'type_only_{value}']=np.where(motif==value,motif,0)
 deleted=motif.copy(); deleted[helper]=0; variants['helper_removed']=deleted
 restored=deleted.copy(); restored[helper]=motif[helper]; variants['rescue']=restored
 # Nonzero-only shuffle preserves composition AND exact initial occupancy mask.
 occupied=np.flatnonzero(motif); shuffled=motif.copy(); shuffled[occupied]=np.roll(motif[occupied],1)
 if np.array_equal(shuffled,motif): shuffled[occupied]=np.roll(motif[occupied],2)
 variants['composition_shuffled_fixed_gaps']=shuffled
 # A wrong-value replacement preserves gap geometry and occupancy at helper site.
 replacement=motif.copy(); replacement[helper]=int(motif[helper])-1; variants['wrong_helper_same_occupancy']=replacement
 # Equal cell loss at another negative site, when one exists, and at positive site.
 others=[int(i) for i in occupied if i!=helper and motif[i]==motif[helper]]
 if others:
  damage=motif.copy(); damage[others[-1]]=0; variants['matched_delete_same_type']=damage
 other=int(next(i for i in occupied if motif[i]>0)); damage=motif.copy(); damage[other]=0; variants['matched_delete_other_type']=damage
 return {name:list(map(int,row)) for name,row in variants.items()},helper

def extract_generated():
 trajectory=read_csv(ROOT/'results/ensemble/conditional3002/trajectory.csv')
 # Declared extraction: earliest row >=10, first four-cell, two-sign motif
 # with >=3 NONOVERLAPPING exact translations. This selects a motif, not
 # a representative run and not a reproductively identified organism.
 for t in range(10,len(trajectory)):
  row=trajectory[t]
  for x in range(len(row)-3):
   motif=row[x:x+4]
   if 99999 in motif or not(np.any(motif>0) and np.any(motif<0)): continue
   p=disjoint(matches(row,motif),4)
   if len(p)>=3: return list(map(int,motif)),{'run':'results/ensemble/conditional3002','time':t,'position':x,'all_match_positions':p,'selection':'first eligible repeated four-cell two-sign window at earliest t>=10'}
 return None,None

def main():
 base=ROOT/'results/assay'; base.mkdir(parents=True,exist_ok=True)
 save_json(base/'design_before_extraction.json',{'width':WIDTH,'steps':STEPS,'placements':PLACEMENTS,'backgrounds':'empty; resident exclusion3001 row24; candidate original ecology if extracted',
  'historical_motif':[5,-3,1,-3,0,-3,1,0],
  'generated_extraction':'earliest t>=10, first four-cell two-sign window with >=3 disjoint exact matches in conditional3002',
  'matching':{'spatial':'all translations, no rotation; position/value tolerance0','temporal':'period-one template; all discrete times searched; extraction time reset as assay t0; no phase pooling'},
  'primary_outcome':'>=2 simultaneous motifs with two empty cells outside each full footprint; each recovered motif must persist for8 steps after isolation; numerical criterion does not itself prove ancestry',
  'secondary_outcomes':['motif persistence last time','unseparated template count','occupied extent/expansion','helper effect and exact rescue'],
  'controls':'single cell loss at same/other types; wrong helper occupies identical site; nonzero shuffle preserves exact occupancy mask',
  'imperfections':['no integer is neutral','deleting another position changes gap geometry differently','resident motif masks replace pre-existing values inside the footprint','exact template can miss viable changed structures','two-cell guard is conservative and excludes contiguous tiling']})
 extracted,origin=extract_generated()
 candidates=[{'id':'historical_figure7','motif':[5,-3,1,-3,0,-3,1,0],'norm':'exclusion','source':{'fixture':'fixtures/fig7.csv','position':20,'time':0}}]
 if extracted: candidates.append({'id':'generated_conditional3002','motif':extracted,'norm':'conditional','source':origin})
 resident=read_csv(ROOT/'results/ensemble/resident3001/trajectory.csv')[-1]
 backgrounds={'empty':np.zeros(WIDTH,dtype=np.int32),'resident':resident}
 save_json(base/'candidates.json',candidates)
 plans=[]
 for candidate in candidates:
  variants,helper=conditions(candidate['motif']); candidate['putative_helper_offset']=helper; candidate['conditions']=variants
  local_backgrounds=dict(backgrounds)
  if candidate['id'].startswith('generated'):
   original=read_csv(ROOT/candidate['source']['run']/'trajectory.csv')[candidate['source']['time']]
   ecology=np.zeros(WIDTH,dtype=np.int32); ecology[86:86+len(original)]=original
   local_backgrounds['original_ecology']=ecology
  for bg,row in local_backgrounds.items():
   np.savetxt(base/f'background_{candidate["id"]}_{bg}.csv',row[None,:],fmt='%d',delimiter=',')
   locations=list(PLACEMENTS)
   if bg=='original_ecology': locations=sorted(set(locations+[86+candidate['source']['position']]))
   for placement,name in itertools.product(locations,variants):
    initial=row.copy(); initial[placement:placement+len(candidate['motif'])]=variants[name]
    ident=f'{candidate["id"]}__{bg}__x{placement}__{name}'
    out=base/ident; out.mkdir(exist_ok=True); np.savetxt(out/'frozen.csv',initial[None,:],fmt='%d',delimiter=',')
    conf={'model':'research','norm':candidate['norm'],'width':WIDTH,'steps':STEPS,'boundary':'open','iteration_order':'ascending','seed':None,'initial_state_file':str((out/'frozen.csv').relative_to(ROOT)),
      'trace_steps':8 if bg=='empty' and placement==112 else 0,
      'modifications':['width256 and paired inoculation/ablation; underlying historical norm unchanged'],
      'assay':{'candidate':candidate['id'],'background':bg,'placement':placement,'condition':name}}
    plans.append({'id':ident,'config':conf})
 # Blank/background-only controls use each candidate norm and same overwritten
 # footprint, so matched generic inoculation effects are visible.
 for candidate in candidates:
  for placement,bg in itertools.product(PLACEMENTS,backgrounds):
   row=backgrounds[bg].copy(); row[placement:placement+len(candidate['motif'])]=0
   ident=f'{candidate["id"]}__{bg}__x{placement}__cleared_footprint'
   out=base/ident; out.mkdir(exist_ok=True); np.savetxt(out/'frozen.csv',row[None,:],fmt='%d',delimiter=',')
   conf={'model':'research','norm':candidate['norm'],'width':WIDTH,'steps':STEPS,'boundary':'open','iteration_order':'ascending','seed':None,'initial_state_file':str((out/'frozen.csv').relative_to(ROOT)),
    'modifications':['paired background control with cleared candidate footprint'], 'assay':{'candidate':candidate['id'],'background':bg,'placement':placement,'condition':'cleared_footprint'}}
   plans.append({'id':ident,'config':conf})
 save_json(base/'candidates.json',candidates)
 save_json(base/'manifest.json',{'declared_before_execution':True,'runs':plans,'recovery_rule':'all distinct candidate motifs are viability probed once in empty width256 at112 for8 updates; detached counts are only potential copies until ancestry supported'})
 rows=[]; bycandidate={c['id']:c for c in candidates}
 for plan in plans:
  conf=plan['config']; out=base/plan['id']; stats=run(conf,out); arr=read_csv(out/'trajectory.csv'); candidate=bycandidate[conf['assay']['candidate']]
  measured=outcome(arr,candidate['motif']); occupied=(arr!=0)&(arr!=99999)
  spans=[int(np.flatnonzero(r)[-1]-np.flatnonzero(r)[0]+1) if r.any() else 0 for r in occupied]
  measured.update(max_occupied_span=max(spans),initial_occupancy=int(occupied[0].sum()),final_occupancy=int(occupied[-1].sum()))
  save_json(out/'outcome.json',measured)
  rows.append({'id':plan['id'],**conf['assay'],**{k:v for k,v in measured.items() if not k.endswith('_by_time') and k!='match_positions_by_time'},'process_seconds':stats['process_seconds'],'max_rss_kib':stats['max_rss_kib']})
 recovery=[]
 for candidate in candidates:
  out=base/(candidate['id']+'__viability'); out.mkdir(exist_ok=True)
  row=np.zeros(WIDTH,dtype=np.int32); row[112:112+len(candidate['motif'])]=candidate['motif']; np.savetxt(out/'frozen.csv',row[None,:],fmt='%d',delimiter=',')
  conf={'model':'research','norm':candidate['norm'],'width':WIDTH,'steps':8,'boundary':'open','seed':None,'initial_state_file':str((out/'frozen.csv').relative_to(ROOT)),'modifications':['eight-step isolated numerical motif recovery check']}
  run(conf,out); arr=read_csv(out/'trajectory.csv')
  recovery.append({'candidate':candidate['id'],'persistent_every_time':all(matches(r,candidate['motif']) for r in arr),'steps':8,'path':str(out.relative_to(ROOT))})
 # This is a paired descriptive assay. Background/placement combinations are
 # deliberately chosen settings, not independent random biological replicates.
 effects=[]
 for candidate in candidates:
  subset=[r for r in rows if r['candidate']==candidate['id']]
  keys=sorted(set((r['background'],r['placement']) for r in subset))
  for bg,placement in keys:
   group={r['condition']:r for r in subset if r['background']==bg and r['placement']==placement}
   intact=group['intact']; removed=group['helper_removed']; rescue=group['rescue']
   effects.append({'candidate':candidate['id'],'background':bg,'placement':placement,
    'intact_persistence':intact['motif_persistence_last_time'],'removed_persistence':removed['motif_persistence_last_time'],'rescue_persistence':rescue['motif_persistence_last_time'],
    'intact_minus_removed':intact['motif_persistence_last_time']-removed['motif_persistence_last_time'],
    'rescue_trajectory_identical':bool(np.array_equal(read_csv(base/intact['id']/'trajectory.csv'),read_csv(base/rescue['id']/'trajectory.csv')))})
 save_json(base/'summary.json',{'rows':rows,'paired_effects':effects,'viability':recovery,'ancestry_claim':'none: source/helper event traces support local copying, motif equality alone is insufficient','reproductive_result':'no additional detached recoverable copies' if max(r['detached_beyond_one'] for r in rows)==0 else 'potential detached copies require ancestry adjudication'})
 with open(base/'summary.csv','w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
 print('assay runs',len(rows),'recovery probes',len(recovery),'candidates',[(c['id'],c['motif']) for c in candidates])
 print('max detached beyond one',max(r['detached_beyond_one'] for r in rows))
 print(json.dumps(effects,indent=2))
if __name__=='__main__': main()
