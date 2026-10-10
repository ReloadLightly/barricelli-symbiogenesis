# SPDX-License-Identifier: GPL-3.0-only
"""Small configuration-driven CLI. Simulation and rendering are separate."""
import argparse, csv, datetime, hashlib, json, pathlib, platform, subprocess, time
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[1]
REFERENCE_COMMIT='beeea928d17c73a66ff5dccee19270ba717596ac'
def sha(path): return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def read_csv(path):
 with open(path) as f: return np.array([[99999 if v.strip().lower()=='x' else int(v) for v in row] for row in csv.reader(f)],dtype=np.int32)
def save_json(path,obj): pathlib.Path(path).write_text(json.dumps(obj,indent=2)+'\n')
def recurrence(arr,environment_period=1):
 seen={}
 for t,row in enumerate(arr):
  key=(t%environment_period,row.tobytes())
  if key in seen: return {'first_time':seen[key],'return_time':t,'period':t-seen[key]}
  seen[key]=t
 return None
def initial_row(config):
 if config.get('initial_state_file'):
  p=pathlib.Path(config['initial_state_file']); p=p if p.is_absolute() else ROOT/p
  row=read_csv(p)[0]
  if len(row)!=config['width']: raise ValueError('initial row width differs from configuration')
  return row
 if config.get('seed') is None: raise ValueError('explicit seed or initial-state file required')
 rng=np.random.Generator(np.random.PCG64(config['seed']))
 mode=config.get('initialization','two_coins')
 if mode=='designed_random':
  alphabet=config['alphabet']; row=rng.choice(alphabet,config['width']).astype(np.int32)
  row[rng.random(config['width'])>=config['density']]=0
  layout=config['layout']; w=config['width']
  mask=np.zeros(w,dtype=bool)
  if layout=='uniform': mask[:]=True
  elif layout=='center_patch': mask[w//4:3*w//4]=True
  elif layout=='two_patches': mask[w//8:3*w//8]=True; mask[5*w//8:7*w//8]=True
  else: raise ValueError('unknown designed layout')
  row[~mask]=0; return row
 if mode=='galloway_float_truncation':
  values=np.float32(-18)+np.float32(37)*rng.random(config['width'],dtype=np.float32)
  values=np.minimum(values,np.nextafter(np.float32(19),np.float32(-np.inf)))
  return np.trunc(values).astype(np.int32)
 if mode=='two_coins': return rng.choice([-1,0,1],config['width'],p=[.25,.5,.25]).astype(np.int32)
 if mode=='resident_exclusion': return rng.choice([-3,0,1,5],config['width'],p=[.2,.5,.2,.1]).astype(np.int32)
 raise ValueError('unknown initialization')
def validate(config):
 model=config['model']; norm=config['norm']
 if model not in ['barricelli1954_reference','galloway_published','research']: raise ValueError('unknown model identifier')
 if config['steps']<0 or config['width']<1: raise ValueError('invalid dimensions')
 if model=='barricelli1954_reference':
  canonical=json.loads((ROOT/f"configs/figure{config['figure']:02d}.json").read_text())
  for key in ['figure','norm','width','steps','initial_state_file']:
   if config[key]!=canonical[key]: raise ValueError(f'reference example changes {key}; use research profile')
  if config.get('seed') is not None: raise ValueError('reference figures use a fixed initial row, not a random seed')
 if model=='galloway_published' and (config['width']!=511 or norm!='galloway_B'):
  raise ValueError('published sketch requires 511 cells and effective B norm')
 if model=='research' and not config.get('modifications'): raise ValueError('research profile must declare modifications')
 expected_boundary='ring' if norm.startswith('galloway_') else 'open'
 if config.get('boundary')!=expected_boundary: raise ValueError('boundary does not match implemented engine')
 if config.get('iteration_order','ascending')!='ascending': raise ValueError('only retrieved ascending order implemented')
 if norm=='galloway_AB_quarters' and (config['width']<4 or config['width']%4): raise ValueError('quarter environment requires width divisible by four')
 if norm=='galloway_AB_halves' and config['width']%2: raise ValueError('matched half environment requires even width')

def run(config,out):
 config=dict(config); validate(config)
 out=pathlib.Path(out); out.mkdir(parents=True,exist_ok=True)
 if not (ROOT/'build/simulator').exists(): subprocess.run(['python3',str(ROOT/'scripts/build.py')],check=True)
 row=initial_row(config); np.savetxt(out/'initial.csv',row[None,:],fmt='%d',delimiter=',')
 save_json(out/'config.json',config)
 source_files=sorted([p for folder in ['engine','barricelli','scripts','configs'] for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in str(p)])
 hashes={str(p.relative_to(ROOT)):sha(p) for p in source_files}
 version=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
 start=time.perf_counter()
 proc=subprocess.run(['/usr/bin/time','-f','{"max_rss_kib":%M,"elapsed_seconds":%e,"user_seconds":%U,"system_seconds":%S}','-o',str(out/'resource.json'),str(ROOT/'build/simulator'),config['model'],config['norm'],str(config['steps']),str(out/'initial.csv'),str(out/'trajectory.csv'),str(out/'statistics.json'),str(out/'events.csv'),str(config.get('trace_steps',0))],capture_output=True,text=True)
 elapsed=time.perf_counter()-start
 if proc.returncode:
  save_json(out/'failure.json',{'returncode':proc.returncode,'stderr':proc.stderr}); raise RuntimeError(proc.stderr)
 arr=read_csv(out/'trajectory.csv'); np.savez_compressed(out/'trajectory.npz',values=arr)
 stats=json.loads((out/'statistics.json').read_text())
 stats['inprocess_rusage_max_rss_kib']=stats['max_rss_kib']
 stats['max_rss_kib']=json.loads((out/'resource.json').read_text())['max_rss_kib']
 valid=(arr!=0)&(arr!=99999)
 stats.update(process_seconds=elapsed,width=arr.shape[1],steps=arr.shape[0]-1,
              final_occupancy=int(valid[-1].sum()),peak_occupancy=int(valid.sum(axis=1).max()),
              unique_valid_values=int(len(np.unique(arr[valid]))),
              values_absent_initial=sorted(set(map(int,arr[valid]))-set(map(int,row[(row!=0)&(row!=99999)]))))
 # Exact whole-world recurrence; residual dynamics carry no organism label.
 stats['environment_period']=2 if config['norm']=='galloway_AB_temporal' else 1
 stats['whole_world_recurrence']=recurrence(arr,stats['environment_period'])
 save_json(out/'statistics.json',stats)
 try: repo_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,stderr=subprocess.DEVNULL,text=True).strip()
 except subprocess.CalledProcessError: repo_head=None
 save_json(out/'provenance.json',{'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
   'reference_commit':REFERENCE_COMMIT,'repository_head':repo_head,'source_tree_sha256':version,'source_files_sha256':hashes,
   'initial_sha256':sha(out/'initial.csv'),'trajectory_sha256':sha(out/'trajectory.csv'),
   'binary_sha256':sha(ROOT/'build/simulator'),'seed':config.get('seed'),
   'random_generator':'NumPy PCG64; float32 then truncation for Galloway' if config.get('seed') is not None else None,
   'platform':platform.platform(),'python':platform.python_version(),'numpy':np.__version__,
   'compiler':subprocess.check_output(['g++','--version'],text=True).splitlines()[0],
   'cpu_only':True,'rss_scope':'native simulator peak RSS; excludes Python plotting/orchestration'})
 return stats

def main():
 p=argparse.ArgumentParser(description=__doc__); p.add_argument('--config',required=True); p.add_argument('--model'); p.add_argument('--seed',type=int); p.add_argument('--initial-state'); p.add_argument('--steps',type=int); p.add_argument('--output',required=True)
 a=p.parse_args(); config=json.loads(pathlib.Path(a.config).read_text())
 for key,value in [('model',a.model),('seed',a.seed),('initial_state_file',a.initial_state),('steps',a.steps)]:
  if value is not None: config[key]=value
 if a.initial_state: config['seed']=None
 stats=run(config,a.output); print(json.dumps(stats,indent=2))
if __name__=='__main__': main()
