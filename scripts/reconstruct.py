#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Predeclare and reproduce all 22 historical examples; benchmark display scale."""
import sys, pathlib, json, hashlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from barricelli.run import ROOT,run,read_csv,save_json
import numpy as np

def main():
 base=ROOT/'results/reconstruction'; base.mkdir(parents=True,exist_ok=True)
 plans=[{'id':f'figure{i:02d}','config':f'configs/figure{i:02d}.json'} for i in range(1,23)]
 plans.append({'id':'galloway2026','config':'configs/galloway_published.json','role':'display-scale throughput benchmark; also ensemble member'})
 manifest={'declared_before_execution':True,'runs':plans}
 save_json(base/'manifest.json',manifest)
 agreement=[]
 for plan in plans:
  conf=json.loads((ROOT/plan['config']).read_text()); stats=run(conf,base/plan['id'])
  if 'figure' in conf:
   actual=read_csv(base/plan['id']/'trajectory.csv'); expected=read_csv(ROOT/conf['initial_state_file'])
   # Confirm BOTH unmodified executable and observation extension against fixtures.
   import subprocess
   raw=subprocess.check_output([str(ROOT/'build/reference'),'-c',str(conf['figure'])],text=True)
   reference=np.array([[99999 if v=='x' else int(v) for v in line.split(',')] for line in raw.splitlines()])
   equal=bool(np.array_equal(actual,expected) and np.array_equal(reference,expected))
   agreement.append({'figure':conf['figure'],'rows':len(actual),'width':actual.shape[1],'cells':actual.size,'exact':equal,'mismatches':int(np.count_nonzero(actual!=expected)),'original_engine_exact':bool(np.array_equal(reference,expected))})
   if not equal: raise RuntimeError(f'fixture discrepancy: {plan["id"]}')
  print(plan['id'],stats['process_seconds'],stats['max_rss_kib'])
 corrected=read_csv(ROOT/'fixtures/fig15-new.csv'); plate=read_csv(ROOT/'fixtures/fig15-orig-from-lalaina-rahobisoa.csv')
 coords=np.argwhere(corrected!=plate)
 save_json(base/'agreement.json',{'fixtures':agreement,'total_cells':sum(a['cells'] for a in agreement),'all_exact':all(a['exact'] for a in agreement),
  'figure15_plate_comparison':{'plate_source':'Rahobisoa plate reconstruction fixture; not direct image transcription here','mismatch_count':len(coords),'first_mismatch_time_zero_based':int(coords[0,0]),'first_row_mismatches':[{'time':int(t),'position':int(x),'computed':int(corrected[t,x]),'plate':int(plate[t,x])} for t,x in coords if t==coords[0,0]],'cells_patched':0}})
if __name__=='__main__': main()
