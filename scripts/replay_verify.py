#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Replay every retained initial row with the current engine; stream comparisons."""
import itertools,json,pathlib,subprocess,sys,tempfile,time
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from barricelli.run import ROOT,sha,save_json
def main():
 rows=json.loads((ROOT/'results/run_register.json').read_text()); results=[]; start=time.perf_counter()
 with tempfile.TemporaryDirectory(prefix='barricelli-replay-') as tmp:
  tmp=pathlib.Path(tmp)
  for row in rows:
   path=ROOT/row['path']; c=json.loads((path/'config.json').read_text())
   subprocess.run([str(ROOT/'build/simulator'),c['model'],c['norm'],str(c['steps']),str(path/'initial.csv'),str(tmp/'trajectory.csv'),str(tmp/'statistics.json'),str(tmp/'events.csv'),'0'],check=True)
   with (tmp/'trajectory.csv').open() as actual,(path/'trajectory.csv').open() as expected:
    mismatched_rows=sum(a!=b for a,b in itertools.zip_longest(actual,expected))
   oracle_mismatches=None
   if (path/'java_oracle.csv').exists():
    with (tmp/'trajectory.csv').open() as actual,(path/'java_oracle.csv').open() as oracle:
     oracle_mismatches=sum(a!=b for a,b in itertools.zip_longest(actual,oracle))
   s=json.loads((tmp/'statistics.json').read_text()); original=json.loads((path/'statistics.json').read_text())
   counter_diffs={k:[original[k],s[k]] for k in ['attempted_copies','accepted_outcomes','collisions','newly_produced_values','erasures','fresh_writes','same_value_outcomes','out_of_bounds','depth_cap'] if original[k]!=s[k]}
   results.append({'path':row['path'],'mismatched_rows':mismatched_rows,'counter_differences':counter_diffs,'frozen_java_oracle_mismatches':oracle_mismatches,'cells':c['width']*(c['steps']+1)})
   if mismatched_rows or counter_diffs or oracle_mismatches: raise RuntimeError('replay failed: '+row['path'])
 save_json(ROOT/'results/replay_verification.json',{'all_exact':True,'native_binary_sha256':sha(ROOT/'build/simulator'),'runs':len(results),'cells':sum(r['cells'] for r in results),'elapsed_seconds':time.perf_counter()-start,'mode':'current engine on saved integer initial states; byte-exact CSV and all nine event-counter comparisons; verification outputs streamed and discarded','records':results})
 print('all exact',len(results),'runs')
if __name__=='__main__': main()
