#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Synthetic numerical control histories for diagnostics, explicitly imposed."""
import json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from barricelli.run import ROOT,save_json
from barricelli.descriptors import describe
import numpy as np

def main():
 base=ROOT/'results/descriptor_controls'; base.mkdir(parents=True,exist_ok=True); rng=np.random.default_rng(7711)
 initial=np.tile([1,-1],64); controls={'static_periodic':np.tile(initial,(257,1)),
  'period_two':np.array([initial if t%2==0 else -initial for t in range(257)]),
  'translation':np.array([np.roll(np.tile([5,-3,1,0],32),t) for t in range(257)]),
  'iid_noise':rng.choice([-9,-7,-3,0,1,5,9,11],(257,128)),
  'empty':np.zeros((257,128),dtype=int)}
 save_json(base/'manifest.json',{'seed':7711,'explicitly_imposed_histories':True,'role':'calibrate descriptors, not simulations or discovered organisms','controls':list(controls),'width':128,'updates':256})
 rows=[]
 for name,arr in controls.items():
  out=base/name; out.mkdir(exist_ok=True); np.savetxt(out/'trajectory.csv',arr,fmt='%d',delimiter=','); np.savetxt(out/'initial.csv',arr[:1],fmt='%d',delimiter=',')
  save_json(out/'config.json',{'model':'descriptor_control','variant':name,'width':128,'steps':256,'seed':7711,'boundary':'ring','intervention':'entire history externally specified; no simulator dynamics'})
  desc=describe(arr,boundary='ring'); rows.append({'id':name,**desc}); save_json(out/'descriptors.json',desc)
 save_json(base/'summary.json',rows); print(json.dumps(rows,indent=2))
if __name__=='__main__': main()
