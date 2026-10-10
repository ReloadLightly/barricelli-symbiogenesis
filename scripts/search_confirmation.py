#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Unseen-state/longer-horizon checks, with a fixed selection rule."""
import json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from barricelli.run import ROOT,run,read_csv,save_json
from barricelli.descriptors import describe
from search import records,METHODS,ALPHABETS
import numpy as np

def main():
 base=ROOT/'results/search_confirmation'; base.mkdir(parents=True,exist_ok=True); plans=[]; selections=[]
 target=np.array([1,1,1,.995])
 for method in METHODS:
  history=[r for repeat in range(4) for r in records(method,repeat)]
  selected=max(history,key=lambda r:np.linalg.norm(np.array(r['descriptors']['vector'])-target))
  selections.append({'method':method,'selected_from':selected['path'],'space_index':selected['space_index'],'theta':selected['theta'],'rule':'largest fixed numerical descriptor distance from the full period-two control; tie favors first recorded run','selection_is_exploratory':True})
  original=json.loads((ROOT/selected['path']/'config.json').read_text())
  for seed in [9100,9101,9102,9103]:
   conf=dict(original); conf.pop('search',None); conf.update(seed=seed,steps=1024,variant='search_confirmation_B'); conf['modifications']=conf['modifications']+['unseen initial state and four-times discovery horizon; no parameter selection on confirmation data']
   plans.append({'id':method+'_'+str(seed),'method':method,'config':conf})
 save_json(base/'manifest.json',{'declared_before_confirmation_execution':True,'selections':selections,'runs':plans,'limited_generalization':'four fresh states per selected configuration; does not establish broad policy superiority'})
 rows=[]
 for plan in plans:
  out=base/plan['id']
  if (out/'descriptors.json').exists(): desc=json.loads((out/'descriptors.json').read_text())
  else:
   stats=run(plan['config'],out); desc=describe(read_csv(out/'trajectory.csv'),stats,boundary=plan['config']['boundary']); save_json(out/'descriptors.json',desc)
  rows.append({'id':plan['id'],'method':plan['method'],'seed':plan['config']['seed'],'path':str(out.relative_to(ROOT)),**desc})
 save_json(base/'summary.json',{'selections':selections,'rows':rows}); print(json.dumps(rows,indent=2))
if __name__=='__main__': main()
