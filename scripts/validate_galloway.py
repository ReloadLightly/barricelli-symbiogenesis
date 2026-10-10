#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Compile unchanged numerical methods from privately cached published PDE in Java.
No third-party program is bundled. Requires retrieved source with pinned hash.
This checks arithmetic/update behavior, not Processing/Processing.js rendering or RNG.
"""
import argparse, pathlib, re, hashlib, json, subprocess, sys, tempfile
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from barricelli.run import ROOT,read_csv,save_json,run
import numpy as np
PDE_SHA='2b39ea4623ca9b350c5127fa324006ec2cdfa5690636f0b89a7ff3aaabfb65ae'
METHODS=['evolve','shift','shiftNorm','zeroNorm','aNorm','bNorm','haveSameSign','getCellValue','getU','getV','getUvalue','getVvalue','isBelowEmptyCell','wrapToUniverse']
def extract(source,name):
 match=re.search(r'(?m)^(?:void|int|boolean) '+name+r'\([^\n]*\)\s*\{',source)
 if not match: raise ValueError('method missing: '+name)
 pos=match.end(); depth=1
 # Strip line comments solely for brace scanning; original body is returned unchanged.
 scan=re.sub(r'//[^\n]*',lambda m:' '*len(m[0]),source)
 while depth:
  if scan[pos]=='{': depth+=1
  elif scan[pos]=='}': depth-=1
  pos+=1
 return source[match.start():pos]
def main():
 p=argparse.ArgumentParser(); p.add_argument('--source',default='/tmp/barricelli-sources/Barricelli.pde'); a=p.parse_args()
 data=pathlib.Path(a.source).read_bytes()
 if hashlib.sha256(data).hexdigest()!=PDE_SHA: raise ValueError('published source hash differs; inspect before validating')
 source=data.decode(); bodies='\n'.join(extract(source,n) for n in METHODS)
 wrapper='''import java.nio.file.*;
public class PublishedOracle {
 int UNIVERSE=511, GENERATIONS; int[][] cells;
 static final int MAX_REPRODUCTIONS=2;
 void execute(String[] args) throws Exception {
  String[] fields=Files.readAllLines(Path.of(args[0])).get(0).split(",");
  GENERATIONS=Integer.parseInt(args[1])+1;
  cells=new int[UNIVERSE][GENERATIONS];
  for(int j=0;j<UNIVERSE;j++) cells[j][0]=Integer.parseInt(fields[j]);
  evolve();
  StringBuilder s=new StringBuilder();
  for(int t=0;t<GENERATIONS;t++) { for(int j=0;j<UNIVERSE;j++) { if(j>0) s.append(','); s.append(cells[j][t]); } s.append('\\n'); }
  Files.writeString(Path.of(args[2]),s.toString());
 }
 public static void main(String[] args) throws Exception { new PublishedOracle().execute(args); }
'''+bodies+'\n}\n'
 base=ROOT/'results/galloway_validation'; base.mkdir(parents=True,exist_ok=True)
 plans=[{'id':f'galloway{s}','path':('results/reconstruction/' if s==2026 else 'results/ensemble/')+f'galloway{s}','steps':511} for s in range(2026,2032)]
 # Adversarial rows exercise seam wrapping, equal helpers, triple erasure/reuse,
 # occupancy-above erasure, collision mutation, and empty-row termination.
 edgecases={'empty':{},'same_helper':{0:1,1:1},'seam':{0:-3,508:5,510:-1},
            'erased_reuse':{8:2,9:1,10:7,11:-1},
            'mutation_under_empty':{8:2,11:-1},'mixed':{0:18,1:-17,5:2,7:-2,508:-9,510:18}}
 for name,entries in edgecases.items():
  row=np.zeros(511,dtype=np.int32)
  for k,v in entries.items(): row[k]=v
  path=base/name; path.mkdir(exist_ok=True); np.savetxt(path/'frozen.csv',row[None,:],delimiter=',',fmt='%d')
  conf=json.loads((ROOT/'configs/galloway_published.json').read_text()); conf.update(initial_state_file=str(path/'frozen.csv'),seed=None,steps=8,trace_steps=2)
  run(conf,path); plans.append({'id':name,'path':str(path.relative_to(ROOT)),'steps':8})
 save_json(base/'manifest.json',{'runs':plans,'source_sha256':PDE_SHA,'method':'unchanged extracted Java-compatible numeric method bodies; source hash verified; fixed integer initial rows'})
 checks=[]
 with tempfile.TemporaryDirectory(prefix='galloway-oracle-') as td:
  td=pathlib.Path(td); (td/'PublishedOracle.java').write_text(wrapper)
  subprocess.run(['javac',str(td/'PublishedOracle.java')],check=True)
  for plan in plans:
   path=ROOT/plan['path']; target=path/'java_oracle.csv'
   subprocess.run(['java','-cp',str(td),'PublishedOracle',str(path/'initial.csv'),str(plan['steps']),str(target)],check=True)
   actual=read_csv(path/'trajectory.csv'); oracle=read_csv(target)
   mismatches=int(np.count_nonzero(actual!=oracle)); checks.append({'id':plan['id'],'cells':actual.size,'mismatches':mismatches,'exact':mismatches==0})
   if mismatches: raise RuntimeError('Galloway oracle mismatch: '+plan['id'])
  # Audit instrumentation branch counts by mechanically adding counters privately.
  audited=wrapper.replace(' int UNIVERSE=511,', ' long b_calls=0,a_calls=0;\n int UNIVERSE=511,')
  audited=audited.replace('void bNorm(int a, int g) {','void bNorm(int a, int g) { b_calls++;').replace('void aNorm(int a, int g) {','void aNorm(int a, int g) { a_calls++;')
  audited=audited.replace('  Files.writeString(Path.of(args[2]),s.toString());','  Files.writeString(Path.of(args[2]),s.toString());\n  System.err.println("B="+b_calls+",A="+a_calls);')
  (td/'PublishedOracle.java').write_text(audited); subprocess.run(['javac',str(td/'PublishedOracle.java')],check=True)
  counts=[]
  for plan in plans[:6]:
   path=ROOT/plan['path']; result=subprocess.run(['java','-cp',str(td),'PublishedOracle',str(path/'initial.csv'),str(plan['steps']),str(td/'count.csv')],capture_output=True,text=True,check=True)
   counts.append({'id':plan['id'],'counts':result.stderr.strip()})
 report={'source_sha256':PDE_SHA,'oracle':'published numerical method bodies compiled with javac; original source numeric methods unchanged for primary comparison','checks':checks,'total_cells':sum(c['cells'] for c in checks),'all_exact':all(c['exact'] for c in checks),'collision_branch_audit':counts,'not_validated':['original Processing UI or Processing.js interpreter','original runtime random initialization stream','pixel identity with published artwork']}
 save_json(base/'agreement.json',report); print(json.dumps(report,indent=2))
if __name__=='__main__': main()
