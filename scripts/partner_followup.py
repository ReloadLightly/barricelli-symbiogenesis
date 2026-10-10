#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Exploratory follow-up chosen from the first assay's observed dependency trace.
All first-assay outcomes are retained. This is not fresh-seed confirmation.
"""
import sys,pathlib,json,csv,itertools
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from barricelli.run import ROOT,run,read_csv,save_json
from barricelli.motifs import outcome
import numpy as np

def main():
 base=ROOT/'results/partner_followup'; base.mkdir(parents=True,exist_ok=True)
 motif=np.array([5,-3,1,-3,0,-3,1,0],dtype=np.int32); helper=5
 variants={'direct_helper_removed':motif.copy(),'rescue':motif.copy(),'same_type_damage_elsewhere':motif.copy(),'wrong_helper_same_occupancy':motif.copy()}
 variants['direct_helper_removed'][helper]=0; variants['same_type_damage_elsewhere'][1]=0; variants['wrong_helper_same_occupancy'][helper]=-4
 backgrounds={'empty':np.zeros(256,dtype=np.int32),'resident':read_csv(ROOT/'results/ensemble/resident3001/trajectory.csv')[-1]}
 plans=[]
 for (bg,row),placement,(name,variant) in itertools.product(backgrounds.items(),[16,112,232],variants.items()):
  ident=f'{bg}__x{placement}__{name}'; out=base/ident; out.mkdir(exist_ok=True)
  initial=row.copy(); initial[placement:placement+8]=variant; np.savetxt(out/'frozen.csv',initial[None,:],delimiter=',',fmt='%d')
  conf={'model':'research','width':256,'steps':48,'norm':'exclusion','boundary':'open','iteration_order':'ascending','seed':None,'initial_state_file':str((out/'frozen.csv').relative_to(ROOT)),'trace_steps':8 if bg=='empty' and placement==112 else 0,
   'modifications':['exploratory dependency-directed helper perturbation after first assay; historical exclusion updates unchanged'],
   'assay':{'candidate':'historical_figure7','background':bg,'placement':placement,'condition':name,'helper_offset':5}}
  plans.append({'id':ident,'config':conf,'paired_intact':f'results/assay/historical_figure7__{bg}__x{placement}__intact'})
 save_json(base/'manifest.json',{'declared_before_execution':True,'exploratory':True,'reason':'first-step trace records 5 at112 assisted by -3 at117 (offset5); first assay targeted offset1, a different -3','runs':plans,'limitations':'exact rescue returns original initial row by construction; no detached reproduction claim; not a fresh-seed confirmation'})
 rows=[]
 for plan in plans:
  out=base/plan['id']; stats=run(plan['config'],out); measured=outcome(read_csv(out/'trajectory.csv'),motif)
  saved={'id':plan['id'],**plan['config']['assay'],**{k:v for k,v in measured.items() if not k.endswith('_by_time') and k!='match_positions_by_time'},'process_seconds':stats['process_seconds'],'max_rss_kib':stats['max_rss_kib']}
  if saved['condition']=='rescue': saved['rescue_identical']=bool(np.array_equal(read_csv(out/'trajectory.csv'),read_csv(ROOT/plan['paired_intact']/'trajectory.csv')))
  else: saved['rescue_identical']=None
  save_json(out/'outcome.json',measured); rows.append(saved)
 save_json(base/'summary.json',{'rows':rows,'result':'direct-helper removal, wrong-value replacement and same-type damage elsewhere must be compared against paired intact outcomes; growth and detached offspring kept separate'})
 with open(base/'summary.csv','w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
 print(json.dumps(rows,indent=2))
if __name__=='__main__': main()
