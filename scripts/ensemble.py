#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Small unselected first ensemble selected from measured display-scale throughput."""
import sys,pathlib,json,csv
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from barricelli.run import ROOT,run,save_json

def main():
 base=ROOT/'results/ensemble'; base.mkdir(parents=True,exist_ok=True)
 bench=json.loads((ROOT/'results/reconstruction/galloway2026/statistics.json').read_text())
 plans=[]
 for seed in range(2026,2032):
  plans.append({'id':f'galloway{seed}','model':'galloway_published','seed':seed,'config':'configs/galloway_published.json',
   'existing_run':'results/reconstruction/galloway2026' if seed==2026 else None})
 for seed in range(3002,3010): plans.append({'id':f'conditional{seed}','model':'research','seed':seed,'config':'configs/research.json'})
 plans.append({'id':'resident3001','model':'research','seed':3001,'config':'configs/research_resident.json'})
 save_json(base/'manifest.json',{'declared_before_execution':True,'basis':{'benchmark_process_seconds':bench['process_seconds'],'benchmark_rss_kib':bench['max_rss_kib'],'decision':'six display-scale Galloway rows, eight historical-scale conditional rows and one resident-background run fit comfortably; no sweep'},'runs':plans,'confirmation_seeds':'9000-9999 reserved at the first ensemble stage; later consumption is declared in search_confirmation and heterogeneity manifests'})
 rows=[]
 for plan in plans:
  conf=json.loads((ROOT/plan['config']).read_text()); conf['seed']=plan['seed']
  path=ROOT/plan['existing_run'] if plan.get('existing_run') else base/plan['id']
  stats=json.loads((path/'statistics.json').read_text()) if plan.get('existing_run') else run(conf,path)
  rows.append({'id':plan['id'],'model':plan['model'],'seed':plan['seed'],'path':str(path.relative_to(ROOT)),**stats})
 save_json(base/'summary.json',rows)
 fields=['id','model','seed','width','steps','engine_seconds','process_seconds','max_rss_kib','final_occupancy','peak_occupancy','unique_valid_values','attempted_copies','accepted_outcomes','collisions','newly_produced_values','erasures','whole_world_recurrence']
 with open(base/'summary.csv','w') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
 print(json.dumps(rows,indent=2))
if __name__=='__main__': main()
